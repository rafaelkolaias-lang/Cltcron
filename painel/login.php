<?php
declare(strict_types=1);

require_once __DIR__ . '/commands/_comum/auth.php';

// Já logado → vai direto para o painel
if (esta_logado()) {
    header('Location: ./index.php');
    exit;
}

$erro = '';

// Verifica bloqueio antes de processar o formulário
$segundos_bloqueio = painel_segundos_bloqueado();
if ($segundos_bloqueio > 0) {
    $minutos = (int)ceil($segundos_bloqueio / 60);
    $erro = "Muitas tentativas incorretas. Tente novamente em {$minutos} minuto(s).";
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $segundos_bloqueio <= 0) {
    $usuario = trim((string)($_POST['usuario'] ?? ''));
    $senha   = (string)($_POST['senha'] ?? '');
    $lembrar = isset($_POST['lembrar']);

    if ($usuario === '' || $senha === '') {
        $erro = 'Preencha usuário e senha.';
    } elseif (!fazer_login($usuario, $senha, $lembrar)) {
        // Recalcula bloqueio (pode ter sido ativado pelo fazer_login)
        $seg = painel_segundos_bloqueado();
        if ($seg > 0) {
            $min = (int)ceil($seg / 60);
            $erro = "Muitas tentativas incorretas. Tente novamente em {$min} minuto(s).";
        } else {
            $erro = 'Usuário ou senha inválidos.';
        }
    } else {
        header('Location: ./index.php');
        exit;
    }
}
?>
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login · RK Produções</title>
  <link rel="icon" type="image/svg+xml" href="./img/favicon.svg">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      min-height: 100vh;
      background: #0b1220;
      background-image:
        radial-gradient(ellipse 60% 50% at 20% 30%, rgba(255,31,91,.08) 0%, transparent 70%),
        radial-gradient(ellipse 50% 40% at 80% 70%, rgba(100,60,200,.07) 0%, transparent 70%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Plus Jakarta Sans', sans-serif;
      color: #e2e8f0;
    }

    .card {
      background: rgba(22, 28, 45, 0.97);
      border: 1px solid rgba(255,255,255,.07);
      border-radius: 12px;
      width: 360px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0,0,0,.5);
    }

    .card-accent { height: 3px; background: linear-gradient(90deg, #1b6ef3, #5b9af8); }

    .card-body { padding: 32px; }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 24px;
    }
    .brand-icon {
      width: 32px; height: 32px;
      background: #e62117;
      border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      font-size: 14px; font-weight: 900; color: #fff; flex-shrink: 0;
    }
    .brand-text { font-size: 15px; font-weight: 700; color: #fff; line-height: 1.2; }
    .brand-sub  { font-size: 10px; font-weight: 500; color: #64748b; letter-spacing: .06em; text-transform: uppercase; }

    h1 { font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px; }
    .subtitulo { font-size: 13px; color: #64748b; margin-bottom: 28px; }

    label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: #64748b;
      letter-spacing: .06em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }

    input[type=text], input[type=password] {
      width: 100%;
      background: rgba(255,255,255,.05);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 7px;
      color: #e2e8f0;
      font-family: inherit;
      font-size: 14px;
      padding: 10px 12px;
      outline: none;
      transition: border-color .15s;
    }
    input[type=text]:focus, input[type=password]:focus {
      border-color: #1b6ef3;
    }
    input::placeholder { color: #4a5568; }

    .campo { margin-bottom: 18px; }

    .lembrar-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 22px;
    }
    .lembrar-row input[type=checkbox] { accent-color: #1b6ef3; width: 15px; height: 15px; cursor: pointer; }
    .lembrar-row span { font-size: 13px; color: #94a3b8; }

    .btn-entrar {
      width: 100%;
      background: #1b6ef3;
      border: none;
      border-radius: 7px;
      color: #fff;
      font-family: inherit;
      font-size: 14px;
      font-weight: 600;
      padding: 11px;
      cursor: pointer;
      transition: background .15s;
    }
    .btn-entrar:hover { background: #1457cc; }

    .erro {
      background: rgba(192,57,43,.15);
      border: 1px solid rgba(192,57,43,.4);
      border-radius: 7px;
      color: #e87070;
      font-size: 13px;
      padding: 10px 12px;
      margin-bottom: 18px;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="card-accent"></div>
    <div class="card-body">

      <div class="brand">
        <div class="brand-icon">▶</div>
        <div>
          <div class="brand-text">RK PRODUÇÕES</div>
          <div class="brand-sub">Painel Administrativo</div>
        </div>
      </div>

      <h1>Bem-vindo</h1>
      <p class="subtitulo">Faça login para acessar o painel.</p>

      <?php if ($erro !== ''): ?>
        <div class="erro"><?= htmlspecialchars($erro) ?></div>
      <?php endif; ?>

      <form method="POST" autocomplete="on">
        <div class="campo">
          <label for="usuario">Usuário</label>
          <input type="text" id="usuario" name="usuario"
                 value="<?= htmlspecialchars($_POST['usuario'] ?? '') ?>"
                 placeholder="Digite seu usuário" autofocus autocomplete="username">
        </div>

        <div class="campo">
          <label for="senha">Senha</label>
          <input type="password" id="senha" name="senha"
                 placeholder="••••••••" autocomplete="current-password">
        </div>

        <div class="lembrar-row">
          <input type="checkbox" id="lembrar" name="lembrar"
                 <?= isset($_POST['lembrar']) ? 'checked' : '' ?>>
          <span><label for="lembrar" style="display:inline;text-transform:none;letter-spacing:0;font-size:13px;color:#94a3b8;cursor:pointer;">Permanecer logado por <?= PAINEL_LEMBRAR_DIAS ?> dias</label></span>
        </div>

        <button type="submit" class="btn-entrar"<?= painel_segundos_bloqueado() > 0 ? ' disabled style="opacity:.5;cursor:not-allowed"' : '' ?>>Entrar</button>
      </form>

    </div>
  </div>
</body>
</html>
