# Linux 原生发送移植：有界观测

仅在本人要求继续开发个人微信发送后端时使用。普通聊天读取仍直接调用 native；这里不是已可用的发送命令。

## 当前源码依据

已按本人要求核对 Windows [WeChat-Hook](https://github.com/aixed/WeChat-Hook/blob/e905d07ade50d2c6472e4eb3bd4f3fe19cf662c6/src/wx_send.cpp)、Mac [wechat_chatter](https://github.com/yincongcyincong/wechat_chatter/blob/04ae61400b9a5754431c10a1455e94c12c4b79e2/onebot/script.js) 和旧版 [linux-wechat-hook](https://github.com/lmclmc/linux-wechat-hook/tree/2631a33cb48001f121f7d164c7ef3a6412f55a84)。前两者确有发送路径，最后一个只实现旧版 Linux 收消息。Windows 的 HTTP 成功码和 Mac 的内部函数返回值均不证明微信服务端送达。

Mac 的业务 protobuf 构造可参考，但 ARM64 调用代码及 Task 模板需要替换。当前 Linux 4.1.13 的离线反汇编已定位 MMStartTask 同族候选 `0x8f53d70 → 0x8f60a90 → 0x8f6dab0`。拷贝函数 `0x8ece4b0` 在 `+0x18` 处理 libc++ 字符串，并访问远超 Mac `0x1A0` 模板的字段；不能把模板原样传入。以上为 ELF 虚拟地址，实际地址需加加载基址，且只适用脚本锁定的二进制 SHA256。腾讯 [Mars Task 定义](https://github.com/Tencent/mars/blob/master/mars/stn/stn.h)可用于解释字段，不能替代当前闭源客户端的布局证据。

## 下一步观测

已安装脚本为 `scripts/native_send_probe.py`，使用系统 GDB 的三个硬件执行断点，最多60秒或合计100次命中。不调用发送函数、不改写消息载荷、不保存聊天正文或凭证、不更改全局 ptrace 设置。断点命中会短暂停住客户端线程以读取参数；结束后删除断点并脱离。只记录两个固定消息 CGI 的任务编号、命令编号、通道字段和最多6层本模块调用地址；对匹配任务再记录序列化回调的返回bool、桥函数模块偏移、两个输出长度及完成回调的错误编号和返回整数，不读取消息正文。

第二个断点位于公共 `StnManager::Req2Buf` 的虚调用返回点 `0x8e828ed`，该处 `ebp=task_id`、`r13=user_context`、`r15=outbuffer`、`r14=extend`、`rbx=manager`，下一条之后才覆盖ebp。通过Task ID和`Task+0x58`的user_context双重关联；context地址仅短期保存在调试器内存，不落盘或解引用。缓冲区只读`+0x10`长度。`manager+0x48 → bridge vtable+0x38`区分默认桥与MM专用桥，记录的地址不冒称最终业务回调。此回调点已有下述真实消息关联证据，SHA及现场指令签名均检查。回调成功也不证明服务端送达。

第三个候选断点位于公共 `StnManager::OnTaskEnd` 的虚调用返回点 `0x8e82d23`，该处 `r13d=task_id`、`r12=user_context`、`r14d=error_type`、`[rsp+0x1c]=error_code`、`eax=callback_result`。错误编号的栈偏移已计入调用前额外压入的两个参数。继续以Task ID/context双重关联，捕获首个匹配完成回调后结束；只捕获Task而未捕获完成回调时，`task_end_event_count`为0，不能当成完整生命周期观测。完成回调返回值不是送达证明，仍需单独验收主动发送及接收端结果。

StartTask同时只读Task的`+0x1c0`打包标志、`+0x60`命令槽、`+0x1c8/+0x1f0`两个AutoBuffer长度。仅当调用帧精确匹配已观察的`0x79e3e9e`，才用该帧保存的r14定位业务对象，记录vtable及其`+0x10`序列化函数的模块偏移和命令编号；不读取业务内容。当前ELF显示Task大小为`0x218`，构造前以`0xaa`填充并调用真实构造函数，发送请求还经过`micromsg.RequestInfo`包装，不能直接塞入原始文字protobuf。以上新增元数据及OnTaskEnd点已通过合成验证，真实微信验证仍待下一轮观测。

先用普通用户运行：

```bash
python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_send_probe.py self-test
```

2026-09-20此自测通过真实 GDB 启动的合成子进程验证了三个硬件断点、`+0x18`字符串解析、打包Task元数据、调用帧业务函数解析、两种回调的错误Task ID/错误context过滤，以及完成回调的有符号错误编号读取；合成验证不替代微信运行时验证。真实观测需要当前桌面用户通过 sudo 启动：

```bash
sudo python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_send_probe.py observe
```

脚本只接受原桌面用户自己的唯一微信主进程，拒绝已有调试器、已停止进程或不匹配的二进制。AppImage的FUSE挂载会检查real/effective/saved UID和GID，不能仅用seteuid/setegid保留root身份。准备阶段在独立子进程中完全切换为原桌面用户，并检查全部六个ID，再读取、校验程序文件和进程映射；root父进程只用短期普通ELF副本供GDB读取，结束删除，不更改挂载或ptrace策略。[内核依据](https://github.com/torvalds/linux/blob/master/fs/fuse/dir.c)与[Python子进程身份参数](https://docs.python.org/3/library/subprocess.html#popen-constructor)。

本人第二轮sudo试跑返回`copy_appimage_as_desktop_user: PermissionError (errno=13)`，说明此前仅切换有效身份的修复不够，仍未开始附加。2026-09-20改用上述子进程后，普通用户已实测同一准备函数能完整复制当前181178912字节FUSE程序、匹配SHA256、解析映射并清理副本；读取子进程的六个ID均匹配桌面用户。CI另用真实root→普通用户切换验证合成文件准备。两项证据各覆盖准备环节，均不代替本人微信的真实sudo观测。

看到“观测已就绪”后，本人在 **这台 Linux 电脑的微信窗口** 向文件传输助手手动发一条短文字，必须在本轮观测结束之前发送。手机发送不会经过正在观测的 Linux 客户端发送入口；结束后才从Linux发送也不会被上一轮记录。就绪提示和结果包含带时区的观测时间，结果另含实际观察时长和等待结束原因；核对发送时机可按已验证的 native messages 读取时间，不必展示消息正文。结果存放在本人 `~/.local/state/ncut-wechat-skills/native-send-observe/run-*/result.json`，权限0600，包含观测结果和是否已脱离、恢复运行的检查。普通账号运行observe会明确返回系统调试权限缺失，不触碰微信。

2026-09-20已在本人Linux微信真实捕获`newsendmsg`：`cmd_id=522`、`channel_select=1`、`transport_protocol=1`；相同Task ID和context关联到了Req2Buf成功返回，桥实现为`0x90718e0`（MM分支），输出长度非零、扩展长度零，退出后已脱离并恢复运行。该验收覆盖只读观测和关联，不代表主动发送能力已接通。

读取结果时：命中只证明该调用及所观察字段，仍需核对请求构造、业务对象及释放规则，才能写真正的发送适配。没有匹配到目标CGI时，先核对发送端和时间；不能凭空换地址或套用 Mac 模板。发送状态不得仅凭观测成功升为runtime_verified。个人身份发送验收继续使用已有明确授权的目标/类型，避免重复询问；新收件人或超出授权范围的内容另行核对。本人暂离且允许ClawBot沟通时，把待协助的本机步骤记入私有状态，通过已授权的bot send联系，避免重发同一事项。
