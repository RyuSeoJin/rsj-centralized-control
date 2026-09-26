/* hdk.js — 부품 초기화 로더. 페이지 <head> 에서 먼저 로드한다.
   부품 파일의 <script> 는 hdk.register('part.variant', function(root){...}) 로 초기화 함수를 등록하고,
   로더가 [data-init="part.variant"] 요소를 찾아 한 번씩 실행한다.
   innerHTML 로 부품을 나중에 끼웠으면 hdk.mount(container) 를 호출한다. */
(function (w) {
  const inits = Object.create(null);
  const hdk = {
    register(name, fn) { inits[name] = fn; hdk.mount(document); },
    mount(container) {
      (container || document).querySelectorAll('[data-init]').forEach(el => {
        if (el.dataset.mounted === 'true') return;
        const fn = inits[el.dataset.init]; if (!fn) return;
        el.dataset.mounted = 'true'; try { fn(el); } catch (e) { console.error('hdk init failed:', el.dataset.init, e); }
      });
    },
    theme(name, mode, root) { const r = root || document.querySelector('.hdk-root'); if (!r) return; if (name) r.dataset.themeName = name; if (mode) r.dataset.theme = mode; }
  };
  w.hdk = hdk;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => hdk.mount(document)); else hdk.mount(document);
})(window);
