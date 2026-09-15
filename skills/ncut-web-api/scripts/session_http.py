"""Shared private CookieJar conversion and bounded school SSO redirects."""
from http.cookiejar import Cookie, CookieJar, DefaultCookiePolicy
import urllib.request as ur
import urllib.error as ue
import urllib.parse as up
import ncut


def follow_login(url, state, max_hops=6):
    jar=cookie_jar(state);chain=[]
    for _ in range(max_hops):
        if ncut.origin(url) not in ncut.allowed_origins():
            return {'ok':False,'code':'UNREGISTERED_AUTH_REDIRECT','chain':chain},state
        headers=ncut.scoped_headers(state,url);headers.pop('Cookie',None)
        try:
            response=ur.build_opener(ncut.NoRedirect,ur.HTTPCookieProcessor(jar)).open(ur.Request(url,headers=headers),timeout=12)
        except ue.HTTPError as error:response=error
        except (ue.URLError,OSError,TimeoutError):
            return {'ok':False,'code':'AUTH_NETWORK_ERROR','chain':chain},state
        with response:
            chain.append({'url':ncut.safe_url(url),'status':response.status})
            location=response.headers.get('Location')
            if 300<=response.status<400 and location:
                url=up.urljoin(url,location);continue
            if len(response.read(ncut.MAX_BYTES+1))>ncut.MAX_BYTES:
                return {'ok':False,'code':'RESPONSE_TOO_LARGE','chain':chain},state
            return {'ok':200<=response.status<300,'code':'AUTH_REDIRECTS_FINISHED','chain':chain},merged_state(state,jar)
    return {'ok':False,'code':'AUTH_REDIRECT_LIMIT','chain':chain},state

def cookie_jar(state):
    jar = CookieJar(policy=DefaultCookiePolicy(strict_ns_domain=DefaultCookiePolicy.DomainStrictNonDomain))
    for c in state.get('cookies', []):
        domain = c['domain']; expires = c.get('expires', -1); rest = {}
        if c.get('httpOnly'): rest['HttpOnly'] = None
        if c.get('sameSite'): rest['SameSite'] = c['sameSite']
        jar.set_cookie(Cookie(0, c['name'], c['value'], None, False, domain, domain.startswith('.'), domain.startswith('.'), c.get('path','/'), True, c.get('secure',False), int(expires) if expires and expires > 0 else None, not expires or expires <= 0, None, None, rest))
    return jar


def merged_state(state, jar):
    old = {(c['domain'],c.get('path','/'),c['name']):c for c in state.get('cookies',[])}
    cookies = []
    for c in jar:
        if c.is_expired() or c.value is None: continue
        item = dict(old.get((c.domain,c.path,c.name), {}))
        item.update(name=c.name,value=c.value,domain=c.domain,path=c.path,secure=c.secure,expires=c.expires if c.expires is not None else -1,httpOnly=c.has_nonstandard_attr('HttpOnly'))
        item.pop('sameSite',None)
        if c.get_nonstandard_attr('SameSite'): item['sameSite'] = c.get_nonstandard_attr('SameSite').capitalize()
        cookies.append(item)
    return {**state, 'cookies':cookies}

