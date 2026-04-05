<?php
declare(strict_types=1);

$arquivo = __DIR__ . '/downloads/CronometroLeve.exe';

if (!file_exists($arquivo)) {
    http_response_code(404);
    exit('Arquivo não encontrado.');
}

header('Content-Description: File Transfer');
header('Content-Type: application/octet-stream');
header('Content-Disposition: attachment; filename="CronometroLeve.exe"');
header('Content-Length: ' . filesize($arquivo));
header('Cache-Control: no-cache, must-revalidate');
header('Pragma: public');

readfile($arquivo);
exit;