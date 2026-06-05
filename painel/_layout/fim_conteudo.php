<?php
// _layout/fim_conteudo.php — fecha a área de conteúdo principal aberta pelo
// topo.php (</main> + rodapé textual + fecha os dois divs do container).
//
// Deve ser incluído DEPOIS das seções da página e ANTES dos modais — os modais
// ficam fora do container `.painel-conteudo` de propósito (evita conflito de
// z-index do Bootstrap quando o modal nasce dentro de um container com overflow).
?>
        </main>

        <footer class="texto-fraco small mt-4" aria-label="Rodapé">
          © Painel ADM · versão banco
        </footer>

    </div>
  </div>
