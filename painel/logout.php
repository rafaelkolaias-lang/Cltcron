<?php
declare(strict_types=1);

require_once __DIR__ . '/commands/_comum/auth.php';

fazer_logout();

header('Location: ./login.php');
exit;
