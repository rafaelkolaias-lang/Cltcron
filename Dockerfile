FROM php:8.1-apache

RUN a2enmod rewrite headers
RUN docker-php-ext-install pdo pdo_mysql

WORKDIR /var/www/html

COPY painel/ /var/www/html/

RUN mkdir -p /var/www/html/downloads \
    && chown -R www-data:www-data /var/www/html

RUN sed -i 's/AllowOverride None/AllowOverride All/g' /etc/apache2/apache2.conf

# Suprimir warning AH00558 (ServerName)
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Diretório de sessões PHP com permissão correta (para uso com volume persistente)
RUN mkdir -p /var/lib/php/sessions && chown www-data:www-data /var/lib/php/sessions

RUN { \
  echo "ServerTokens Prod"; \
  echo "ServerSignature Off"; \
} > /etc/apache2/conf-available/security-hardening.conf \
  && a2enconf security-hardening

EXPOSE 80