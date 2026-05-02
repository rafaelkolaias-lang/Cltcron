<?php
declare(strict_types=1);

// Primeiro tenta servir o .exe local (build manual / XAMPP)
$arquivo = __DIR__ . '/downloads/CronometroLeve.exe';

if (file_exists($arquivo)) {
    header('Content-Description: File Transfer');
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="CronometroLeve.exe"');
    header('Content-Length: ' . filesize($arquivo));
    header('Cache-Control: no-cache, must-revalidate');
    header('Pragma: public');
    readfile($arquivo);
    exit;
}

// Fallback: redireciona para a release mais recente no GitHub
$url_release = 'https://github.com/rafaelkolaias-lang/Cltcron/releases/latest/download/CronometroLeve.exe';

header('Location: ' . $url_release, true, 302);
exit;