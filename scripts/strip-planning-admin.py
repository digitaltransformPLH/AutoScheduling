from pathlib import Path
import re

PLANNING = Path(__file__).resolve().parents[1] / "PLH Weekly Workforce Planning.html"

API_SCRIPT = """<script>
(function(){
  if(window.__plApiBaseUrl) return;
  var path=(location.pathname||'/').replace(/\\/g,'/');
  path=path.replace(/\\/index\\.html$/i,'').replace(/\\/+$/,'');
  if(/\\/planning(\\/|$)/i.test(path)){
    var root=path.replace(/\\/planning(\\/.*)?$/i,'');
    if(root==='/'||root==='') root='';
    window.__plApiBaseUrl=(root||'')+'/api/v1';
    return;
  }
  if(path==='/'||path===''){ window.__plApiBaseUrl='/api/v1'; return; }
  window.__plApiBaseUrl=path+'/api/v1';
})();
</script>"""

BOOT_SCRIPT = """
<script id="pl-planning-auth-script">
(function(){
  'use strict';
  const API=()=>String(window.__plApiBaseUrl||'/api/v1').replace(/\\/$/,'');
  async function boot(){
    try{
      const r=await fetch(`${API()}/me`,{credentials:'include',headers:{'Accept':'application/json'}});
      if(!r.ok){
        const ret=encodeURIComponent(location.pathname+location.search);
        window.location.href='/login?return='+ret;
        return;
      }
      const me=await r.json();
      window.__plMe=me;
      window.dispatchEvent(new CustomEvent('pl-auth-ready',{detail:me}));
    }catch(e){
      window.location.href='/login';
    }
  }
  window.addEventListener('DOMContentLoaded',()=>{
    const tryBoot=()=>{ if(document.querySelector('.app-shell')) boot(); else setTimeout(tryBoot,120); };
    setTimeout(tryBoot,200);
  });
})();
</script>
"""


def main() -> None:
    text = PLANNING.read_text(encoding="utf-8")

    style_marker = '<style id="pl-auth-admin-style">'
    zone_marker = '<script id="pl-zone-board-v5-script">'
    i0 = text.find(style_marker)
    i1 = text.find(zone_marker)
    if i0 == -1 or i1 == -1:
        raise SystemExit("Admin block markers missing — already stripped?")
    text = text[:i0] + BOOT_SCRIPT + text[i1:]

    text, n = re.subn(
        r"<script>\s*\(function\(\)\{[\s\S]*?__plApiBaseUrl[\s\S]*?\}\)\(\);\s*</script>",
        API_SCRIPT,
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"API script replace failed (count={n})")

    PLANNING.write_text(text, encoding="utf-8")
    print("OK:", PLANNING)


if __name__ == "__main__":
    main()
