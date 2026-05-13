// server.c
// gcc server.c -o server -lpthread

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>

#define HOST "0.0.0.0"
#define PORT 5000

typedef struct {
    int src;
    int dst;
} RelayArgs;

int send_packet(int sock, const uint8_t *data, uint32_t length) {
    uint32_t net_len = htonl(length);

    if (send(sock, &net_len, sizeof(net_len), 0) != sizeof(net_len)) {
        return -1;
    }

    uint32_t total = 0;
    while (total < length) {
        ssize_t sent = send(sock, data + total, length - total, 0);
        if (sent <= 0) {
            return -1;
        }
        total += sent;
    }

    return 0;
}

int recv_exact(int sock, uint8_t *buffer, uint32_t size) {
    uint32_t total = 0;

    while (total < size) {
        ssize_t received = recv(sock, buffer + total, size - total, 0);

        if (received <= 0) {
            return -1;
        }

        total += received;
    }

    return 0;
}

uint8_t *recv_packet(int sock, uint32_t *out_length) {
    uint32_t net_len;

    if (recv_exact(sock, (uint8_t *)&net_len, sizeof(net_len)) < 0) {
        return NULL;
    }

    uint32_t length = ntohl(net_len);
    uint8_t *buffer = malloc(length);

    if (!buffer) {
        return NULL;
    }

    if (recv_exact(sock, buffer, length) < 0) {
        free(buffer);
        return NULL;
    }

    *out_length = length;
    return buffer;
}

void *forward_thread(void *arg) {
    RelayArgs *args = (RelayArgs *)arg;

    while (1) {
        uint32_t length;
        uint8_t *data = recv_packet(args->src, &length);

        if (!data) {
            break;
        }

        if (send_packet(args->dst, data, length) < 0) {
            free(data);
            break;
        }

        free(data);
    }

    close(args->src);
    close(args->dst);
    free(args);

    return NULL;
}

void relay(int a, int b) {
    pthread_t t1, t2;

    RelayArgs *args1 = malloc(sizeof(RelayArgs));
    RelayArgs *args2 = malloc(sizeof(RelayArgs));

    args1->src = a;
    args1->dst = b;

    args2->src = b;
    args2->dst = a;

    pthread_create(&t1, NULL, forward_thread, args1);
    pthread_create(&t2, NULL, forward_thread, args2);

    pthread_detach(t1);
    pthread_detach(t2);
}

int main() {
    int server_fd;
    struct sockaddr_in server_addr;

    int waiting[2];
    int waiting_count = 0;

    server_fd = socket(AF_INET, SOCK_STREAM, 0);

    if (server_fd < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 10) < 0) {
        perror("listen");
        close(server_fd);
        return 1;
    }

    printf("Server running at %s:%d\n", HOST, PORT);

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);

        int client_fd = accept(server_fd,
                               (struct sockaddr *)&client_addr,
                               &addr_len);

        if (client_fd < 0) {
            perror("accept");
            continue;
        }

        printf("Connected: %s:%d\n",
               inet_ntoa(client_addr.sin_addr),
               ntohs(client_addr.sin_port));

        waiting[waiting_count++] = client_fd;

        if (waiting_count >= 2) {
            int a = waiting[0];
            int b = waiting[1];

            waiting_count = 0;

            printf("Pairing clients\n");

            relay(a, b);
        }
    }

    close(server_fd);
    return 0;
}