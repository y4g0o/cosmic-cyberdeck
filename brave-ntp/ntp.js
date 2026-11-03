// relógio + atalhos editáveis (salvos no localStorage da extensão; nada de rede)
const dias = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
const p2 = (n) => String(n).padStart(2, "0");
function tique() {
  const d = new Date();
  document.getElementById("hora").textContent = `${p2(d.getHours())}:${p2(d.getMinutes())}`;
  document.getElementById("data").textContent =
    `${dias[d.getDay()]} ${p2(d.getDate())}.${p2(d.getMonth() + 1)}.${d.getFullYear()}  //  ${p2(d.getSeconds())}s`;
}
tique();
setInterval(tique, 1000);

const PADRAO = [
  ["GITHUB", "https://github.com"], ["YOUTUBE", "https://www.youtube.com"], ["WIKIPEDIA", "https://www.wikipedia.org"],
  ["REDDIT", "https://www.reddit.com"], ["MAPS", "https://www.openstreetmap.org"], ["MAIL", "https://mail.proton.me"],
  ["NEWS", "https://news.ycombinator.com"], ["MUSIC", "https://open.spotify.com"],
];
const CHAVE = "cyberdeck.atalhos";
let atalhos, editando = false, alvo = null;
try { atalhos = JSON.parse(localStorage.getItem(CHAVE)) || PADRAO; } catch { atalhos = PADRAO; }
const salvar = () => { try { localStorage.setItem(CHAVE, JSON.stringify(atalhos)); } catch {} };

const nav = document.getElementById("atalhos");
const form = document.getElementById("editor");
const nome = document.getElementById("ed-nome"), url = document.getElementById("ed-url");

function desenhar() {
  nav.replaceChildren();
  document.body.classList.toggle("modo-edicao", editando);
  atalhos.forEach(([n, u], i) => {
    const a = document.createElement("a");
    a.href = u;
    a.innerHTML = `<b></b><i>${p2(i + 1)}</i>`;
    a.querySelector("b").textContent = n;
    if (editando) {
      a.addEventListener("click", (e) => { e.preventDefault(); abrir(i); });
      const ctl = document.createElement("span");
      ctl.className = "ctl";
      ctl.innerHTML = '<button data-a="esq">◀</button><button data-a="dir">▶</button><button data-a="del">✕</button>';
      ctl.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation();
        const acao = e.target.dataset.a;
        if (acao === "del") atalhos.splice(i, 1);
        if (acao === "esq" && i > 0) [atalhos[i - 1], atalhos[i]] = [atalhos[i], atalhos[i - 1]];
        if (acao === "dir" && i < atalhos.length - 1) [atalhos[i + 1], atalhos[i]] = [atalhos[i], atalhos[i + 1]];
        salvar(); desenhar();
      });
      a.appendChild(ctl);
    }
    nav.appendChild(a);
  });
  if (editando) {
    const mais = document.createElement("a");
    mais.href = "#"; mais.className = "mais"; mais.innerHTML = "<b>+ ADD</b>";
    mais.addEventListener("click", (e) => { e.preventDefault(); abrir(null); });
    nav.appendChild(mais);
  }
}
function abrir(i) {
  alvo = i;
  nome.value = i === null ? "" : atalhos[i][0];
  url.value = i === null ? "https://" : atalhos[i][1];
  form.hidden = false; nome.focus();
}
form.addEventListener("submit", (e) => {
  e.preventDefault();
  let u = url.value.trim();
  if (!/^https?:\/\//.test(u)) u = "https://" + u;
  const item = [nome.value.trim().toUpperCase().slice(0, 16), u];
  if (alvo === null) atalhos.push(item); else atalhos[alvo] = item;
  salvar(); form.hidden = true; desenhar();
});
document.getElementById("ed-cancelar").addEventListener("click", () => { form.hidden = true; });
document.getElementById("editar").addEventListener("click", (e) => {
  editando = !editando; form.hidden = true;
  e.target.textContent = editando ? "DONE" : "EDIT";
  desenhar();
});
desenhar();
