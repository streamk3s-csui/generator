#!/bin/bash

until rabbitmqctl status >/dev/null 2>&1; do
  echo "Waiting for RabbitMQ to start..."
  sleep 5
done

if ! rabbitmqctl list_vhosts | grep -q "test"; then
  echo "Creating vhost 'test'"
  rabbitmqctl add_vhost test
fi

echo "Setting permissions for 'user' on 'test' vhost"
rabbitmqctl set_permissions -p test user ".*" ".*" ".*"

touch /var/lib/rabbitmq/setup_complete