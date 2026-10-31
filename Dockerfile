FROM php:8.2-apache

# Enable Apache mod_rewrite for .htaccess protection
RUN a2enmod rewrite

# Copy khoroch web and backend files into Apache document root
COPY khoroch/ /var/www/html/

# Set up permissions for SQLite data directory
RUN mkdir -p /var/www/html/data && \
    chown -R www-data:www-data /var/www/html && \
    chmod -R 775 /var/www/html/data

EXPOSE 80

CMD ["apache2-foreground"]
