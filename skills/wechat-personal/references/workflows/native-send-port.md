# Linux 原生发送移植：有界观测

仅在本人要求继续开发个人微信发送后端时使用。普通聊天读取仍直接调用 native；这里不是已可用的发送命令。

## 当前源码依据

已按本人要求核对 Windows [WeChat-Hook](https://github.com/aixed/WeChat-Hook/blob/e905d07ade50d2c6472e4eb3bd4f3fe19cf662c6/src/wx_send.cpp)、Mac [wechat_chatter](https://github.com/yincongcyincong/wechat_chatter/blob/04ae61400b9a5754431c10a1455e94c12c4b79e2/onebot/script.js) 和旧版 [linux-wechat-hook](https://github.com/lmclmc/linux-wechat-hook/tree/2631a33cb48001f121f7d164c7ef3a6412f55a84)。前两者确有发送路径，最后一个只实现旧版 Linux 收消息。Windows 的 HTTP 成功码和 Mac 的内部函数返回值均不证明微信服务端送达。

Mac 的业务 protobuf 构造可参考，但 ARM64 调用代码及 Task 模板需要替换。当前 Linux 4.1.13 的离线反汇编已定位 MMStartTask 同族候选 `0x8f53d70 → 0x8f60a90 → 0x8f6dab0`。拷贝函数 `0x8ece4b0` 在 `+0x18` 处理 libc++ 字符串，并访问远超 Mac `0x1A0` 模板的字段；不能把模板原样传入。以上为 ELF 虚拟地址，实际地址需加加载基址，且只适用脚本锁定的二进制 SHA256。腾讯 [Mars Task 定义](https://github.com/Tencent/mars/blob/master/mars/stn/stn.h)可用于解释字段，不能替代当前闭源客户端的布局证据。

## 下一步观测

已安装脚本为 `scripts/native_send_probe.py`，使用系统 GDB 的硬件执行断点，最多60秒或100次命中。不调用发送函数、不改写消息载荷、不保存聊天正文或凭证、不更改全局 ptrace 设置。断点命中会短暂停住客户端线程以读取参数；结束后删除断点并脱离。只记录两个固定消息 CGI 的任务编号、命令编号、通道字段和最多6层本模块调用地址，不读取消息正文。

先用普通用户运行：

```bash
python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_send_probe.py self-test
```

2026-09-20此自测通过真实 GDB 启动的合成子进程验证了硬件断点及 `+0x18` 字符串解析，未验证微信运行时。真实观测需要当前桌面用户通过 sudo 启动：

```bash
sudo python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_send_probe.py observe
```

脚本只接受原桌面用户自己的唯一微信主进程，拒绝已有调试器、已停止进程或不匹配的二进制。AppImage的FUSE挂载会检查real/effective/saved UID和GID，不能仅用seteuid/setegid保留root身份。准备阶段在独立子进程中完全切换为原桌面用户，并检查全部六个ID，再读取、校验程序文件和进程映射；root父进程只用短期普通ELF副本供GDB读取，结束删除，不更改挂载或ptrace策略。[内核依据](https://github.com/torvalds/linux/blob/master/fs/fuse/dir.c)与[Python子进程身份参数](https://docs.python.org/3/library/subprocess.html#popen-constructor)。

本人第二轮sudo试跑返回`copy_appimage_as_desktop_user: PermissionError (errno=13)`，说明此前仅切换有效身份的修复不够，仍未开始附加。2026-09-20改用上述子进程后，普通用户已实测同一准备函数能完整复制当前181178912字节FUSE程序、匹配SHA256、解析映射并清理副本；读取子进程的六个ID均匹配桌面用户。CI另用真实root→普通用户切换验证合成文件准备。两项证据各覆盖准备环节，均不代替本人微信的真实sudo观测。

看到“观测已就绪”后，本人在 **这台 Linux 电脑的微信窗口** 向文件传输助手手动发一条短文字，必须在本轮观测结束之前发送。手机发送不会经过正在观测的 Linux 客户端发送入口；结束后才从Linux发送也不会被上一轮记录。就绪提示和结果包含带时区的观测时间，结果另含实际观察时长和等待结束原因；核对发送时机可按已验证的 native messages 读取时间，不必展示消息正文。结果存放在本人 `~/.local/state/ncut-wechat-skills/native-send-observe/run-*/result.json`，权限0600，包含观测结果和是否已脱离、恢复运行的检查。普通账号运行observe会明确返回系统调试权限缺失，不触碰微信。

读取结果时：命中只证明该调用及所观察字段，仍需验证 Req2Buf、回调对象、线程和释放规则，才能写真正的发送适配。没有匹配到目标CGI时，先核对发送端和时间；不能凭空换地址或套用 Mac 模板。准备、真实附加、候选断点命中与清理流程已有本人微信实测；消息发送Task字段尚未捕获，发送状态不得升为 runtime_verified。个人身份发送验收继续使用已有明确授权的目标/类型，避免重复询问；新收件人或超出授权范围的内容另行核对。本人暂离且允许ClawBot沟通时，把待协助的本机步骤记入私有状态，通过已授权的bot send联系，避免重发同一事项。
