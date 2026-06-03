<?php
// _layout/rodape.php — rodapé compartilhado: scripts base + scripts da página +
// núcleo (painel.js) + toggle da sidebar mobile, e fecha <body>/<html>.
//
// Incluído por último, DEPOIS dos modais da página.
//
// Parâmetro opcional (definir ANTES do require):
//   $scriptsAba (array) — srcs de <script> específicos da página (ex.:
//                         ['./js/aba-relatorio.js?v=8']). Carregados ENTRE os
//                         scripts base e o painel.js (núcleo), preservando a
//                         ordem original do index.php.

$scriptsAba = $scriptsAba ?? [];
?>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

<?php foreach ($scriptsAba as $_src): ?>
  <script src="<?= htmlspecialchars($_src, ENT_QUOTES, 'UTF-8') ?>"></script>
<?php endforeach; ?>
  <script src="./js/painel.js?v=9"></script>
  <script>
    // Toggle da sidebar no mobile. Em desktop a sidebar fica fixa e o
    // botão ☰ não é exibido — esse script só importa em ≤ md.
    (function () {
      const body = document.body;
      const btn = document.getElementById("botaoAbrirSidebar");
      const overlay = document.getElementById("painelSidebarOverlay");
      function fechar() { body.classList.remove("painel-sidebar-aberta"); }
      if (btn) btn.addEventListener("click", () => body.classList.toggle("painel-sidebar-aberta"));
      if (overlay) overlay.addEventListener("click", fechar);
      // Fecha ao clicar num link de aba (UX mobile: vai pra aba sem deixar overlay aberto)
      document.querySelectorAll('#menuAbas a[data-aba]').forEach((a) => {
        a.addEventListener("click", () => { if (window.innerWidth < 992) fechar(); });
      });
    })();
  </script>
</body>

</html>
