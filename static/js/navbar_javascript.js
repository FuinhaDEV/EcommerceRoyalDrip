document.addEventListener("DOMContentLoaded", function () {
  const botoesFiltro = document.querySelectorAll(".btn-filtro");
  const produtos = document.querySelectorAll(".produto-card");

  if (!botoesFiltro.length || !produtos.length) return;

  botoesFiltro.forEach((botao) => {
    botao.addEventListener("click", function (e) {
      e.preventDefault();

      // 1. Destacar o botão clicado
      botoesFiltro.forEach((btn) => btn.classList.remove("active"));
      this.classList.add("active");

      // 2. Pegar a categoria do botão
      const filtro = this.getAttribute("data-filter");

      // 3. Filtrar produtos
      produtos.forEach((produto) => {
        const categoria = produto.getAttribute("data-categoria");

        if (filtro === "todos" || categoria === filtro) {
          produto.classList.remove("escondido");
        } else {
          produto.classList.add("escondido");
        }
      });
    });
  });
});