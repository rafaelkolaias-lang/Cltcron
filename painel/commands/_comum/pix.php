<?php
declare(strict_types=1);

/**
 * pix.php — validador de chave Pix (espelho de app/validador_pix.py).
 *
 * Aceita: CNPJ (14 dígitos, DV válido), celular BR (10–11 dígitos com DDD),
 * e-mail (formato básico). Recusa explicitamente CPF e qualquer outro formato.
 *
 * API:
 *   pix_validar(string $texto): array { tipo: 'cnpj'|'celular'|'email', valor: string }
 *     Levanta InvalidArgumentException com mensagem amigável em caso de falha.
 */

if (!function_exists('pix_so_digitos')) {
    function pix_so_digitos(string $texto): string
    {
        return preg_replace('/\D+/', '', $texto) ?? '';
    }

    function pix_validar_cnpj(string $digitos): bool
    {
        if (strlen($digitos) !== 14) return false;
        if (preg_match('/^(\d)\1{13}$/', $digitos)) return false;
        $pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
        $pesos2 = array_merge([6], $pesos1);
        $soma = 0;
        for ($i = 0; $i < 12; $i++) $soma += ((int)$digitos[$i]) * $pesos1[$i];
        $dv1 = ($soma % 11 < 2) ? 0 : 11 - ($soma % 11);
        if ($dv1 !== (int)$digitos[12]) return false;
        $soma = 0;
        for ($i = 0; $i < 13; $i++) $soma += ((int)$digitos[$i]) * $pesos2[$i];
        $dv2 = ($soma % 11 < 2) ? 0 : 11 - ($soma % 11);
        return $dv2 === (int)$digitos[13];
    }

    function pix_validar_celular_br(string $digitos): bool
    {
        $len = strlen($digitos);
        if ($len !== 10 && $len !== 11) return false;
        $ddd = (int)substr($digitos, 0, 2);
        if ($ddd < 11 || $ddd > 99) return false;
        if ($len === 11 && $digitos[2] !== '9') return false;
        return true;
    }

    /**
     * @return array{tipo:string,valor:string}
     * @throws InvalidArgumentException
     */
    function pix_validar(string $texto): array
    {
        $bruto = trim($texto);
        if ($bruto === '') {
            throw new InvalidArgumentException('Informe a chave Pix.');
        }

        if (str_contains($bruto, '@')) {
            $valor = strtolower($bruto);
            if (!preg_match('/^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/', $valor)) {
                throw new InvalidArgumentException('E-mail inválido. Verifique o formato (ex: nome@dominio.com).');
            }
            return ['tipo' => 'email', 'valor' => $valor];
        }

        $digitos = pix_so_digitos($bruto);
        if ($digitos === '') {
            throw new InvalidArgumentException('Chave inválida. Use CNPJ, celular ou e-mail.');
        }

        $len = strlen($digitos);

        if ($len === 11 && !pix_validar_celular_br($digitos)) {
            throw new InvalidArgumentException(
                'CPF não é aceito como chave Pix neste sistema. Use CNPJ, celular ou e-mail.'
            );
        }
        if (($len === 11 || $len === 10) && pix_validar_celular_br($digitos)) {
            return ['tipo' => 'celular', 'valor' => $digitos];
        }
        if ($len === 14) {
            if (!pix_validar_cnpj($digitos)) {
                throw new InvalidArgumentException('CNPJ inválido. Confira os dígitos.');
            }
            return ['tipo' => 'cnpj', 'valor' => $digitos];
        }

        throw new InvalidArgumentException(
            'Chave inválida. Use CNPJ (14 dígitos), celular (10–11 dígitos) ou e-mail.'
        );
    }
}
