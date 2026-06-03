<?php
// _layout/topo.php — cabeçalho compartilhado de TODAS as páginas do painel.
// Inclui: guard de sessão, <head>, topbar (mobile), sidebar (menu lateral) e
// abre o container/<main>. Cada página inclui este arquivo no topo.
//
// Parâmetros opcionais (definir ANTES do require, senão usa o default):
//   $tituloPagina    (string) — <title> da página
//   $subtituloPagina (string) — texto pequeno abaixo da marca, na sidebar
//   $abaAtiva        (string) — id da aba ativa (ex.: 'abaRelatorio') p/ marcar
//                               o item correspondente no menu como `active`
//   $cssExtra        (array)  — hrefs de <link rel=stylesheet> extras da página
//
// Observação sobre o menu: cada link guarda `data-aba` (usado pela navegação
// SPA do index.php) e, por ora, `href="#"`. Conforme cada seção virar página
// própria, o href do item correspondente passa a apontar pra essa página —
// como o menu é compartilhado, a troca vale em todas as páginas de uma vez.

require_once __DIR__ . '/../commands/_comum/auth.php';
if (!esta_logado()) {
    header('Location: ./login.php');
    exit;
}
header('Content-Type: text/html; charset=utf-8');

$tituloPagina    = $tituloPagina    ?? 'Painel ADM · RK Produções Digitais';
$subtituloPagina = $subtituloPagina ?? 'Dashboard · visão geral';
$abaAtiva        = $abaAtiva        ?? 'abaDashboard';
$cssExtra        = $cssExtra        ?? [];

/** Devolve a classe do link do menu, marcando `active` quando for a aba atual. */
$_classeNav = static function (string $aba) use ($abaAtiva): string {
    return $aba === $abaAtiva ? 'nav-link active' : 'nav-link';
};
?>
<!doctype html>
<html lang="pt-br">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= htmlspecialchars($tituloPagina, ENT_QUOTES, 'UTF-8') ?></title>

  <link rel="icon" type="image/svg+xml" href="./img/favicon.svg">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="./css/painel.css?v=10" rel="stylesheet">
<?php foreach ($cssExtra as $_css): ?>
  <link href="<?= htmlspecialchars($_css, ENT_QUOTES, 'UTF-8') ?>" rel="stylesheet">
<?php endforeach; ?>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
</head>

<body>
  <!-- Topbar visível só em telas pequenas (até md). Em desktop, navegação fica
       inteira na sidebar à esquerda. -->
  <nav class="painel-topbar d-lg-none" aria-label="Navegação (mobile)">
    <button class="btn btn-sm btn-outline-light" id="botaoAbrirSidebar" type="button" aria-label="Abrir menu">☰</button>
    <a class="navbar-brand d-flex align-items-center gap-2 text-decoration-none ms-2" href="#">
      <span class="rk-logo-icon" aria-hidden="true"><span class="rk-play">&#9654;</span></span>
      <span class="rk-logo-texto">
        <span class="rk-sigla">RK</span><span class="rk-producoes">PRODUÇÕES</span>
      </span>
    </a>
  </nav>

  <!-- Overlay do mobile (clica fora pra fechar) -->
  <div class="painel-sidebar-overlay" id="painelSidebarOverlay" aria-hidden="true"></div>

  <aside class="painel-sidebar" id="painelSidebar" aria-label="Navegação principal">
    <div class="painel-sidebar-topo">
      <a class="painel-sidebar-marca d-flex align-items-center gap-2 text-decoration-none" href="#">
        <span class="rk-logo-icon" aria-hidden="true"><span class="rk-play">&#9654;</span></span>
        <span class="rk-logo-texto">
          <span class="rk-sigla">RK</span><span class="rk-producoes">PRODUÇÕES</span>
        </span>
        <span class="badge badge-suave fw-normal small ms-1">ADM</span>
      </a>
      <span class="texto-fraco small mt-2 d-block" id="textoSubtitulo"><?= htmlspecialchars($subtituloPagina, ENT_QUOTES, 'UTF-8') ?></span>
    </div>

    <ul class="painel-sidebar-nav" id="menuAbas">
      <li class="nav-item">
        <a class="<?= $_classeNav('abaDashboard') ?>" href="./index.php" data-aba="abaDashboard">Dashboard</a>
      </li>
      <li class="nav-item nav-hover-submenu">
        <a class="<?= $_classeNav('abaUsuarios') ?>" href="./index.php?aba=abaUsuarios" data-aba="abaUsuarios">Usuários</a>
        <ul class="submenu-nav">
          <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalAdicionarUsuario">+ Adicionar Usuário</a></li>
        </ul>
      </li>
      <li class="nav-item nav-hover-submenu">
        <a class="<?= $_classeNav('abaAtividades') ?>" href="./canal.php">Canal</a>
        <ul class="submenu-nav">
          <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">+ Adicionar Canal</a></li>
        </ul>
      </li>
      <li class="nav-item">
        <a class="<?= $_classeNav('abaGerenciarTarefas') ?>" href="./gerenciar-tarefas.php">Gerenciar Tarefas</a>
      </li>
      <li class="nav-item nav-hover-submenu">
        <a class="<?= $_classeNav('abaCredenciais') ?>" href="./credenciais.php">Credenciais e APIs</a>
        <ul class="submenu-nav">
          <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalGerenciarModelos">⚙ Gerenciar modelos</a></li>
        </ul>
      </li>
      <li class="nav-item">
        <a class="<?= $_classeNav('abaRelatorio') ?>" href="./relatorio.php">Relatório</a>
      </li>
      <li class="nav-item">
        <a class="<?= $_classeNav('abaAuditoria') ?>" href="./auditoria.php" id="linkAbaAuditoria" title="Auditoria de apps suspeitos"><span id="linkAbaAuditoriaIcone" class="d-none">🚨 </span>Auditoria</a>
      </li>
      <li class="nav-item">
        <a class="<?= $_classeNav('abaMega') ?>" href="./index.php?aba=abaMega" data-aba="abaMega" title="Configuração de upload obrigatório no MEGA">MEGA</a>
      </li>
      <li class="nav-item">
        <a class="<?= $_classeNav('abaLogAtividades') ?>" href="./log.php" title="Log de todas as ações do servidor">Log</a>
      </li>
    </ul>

    <!-- Bloco inferior: ações globais (Sair / Baixar App / Recarregar). -->
    <div class="painel-sidebar-rodape">
      <button class="btn btn-sm btn-outline-light w-100" type="button" id="botaoRecarregarAba" title="Recarregar aba atual">&#x21BB; Recarregar</button>
      <a href="./baixar_app.php" class="btn btn-sm btn-light w-100">Baixar App</a>
      <a href="./logout.php" class="btn btn-sm btn-outline-danger w-100" title="Sair do painel">Sair</a>
    </div>
  </aside>

  <div class="container-fluid painel-conteudo">
    <div class="p-3 p-md-4">

        <section id="areaAlertas" aria-label="Mensagens do sistema"></section>

        <main aria-label="Conteúdo principal">
