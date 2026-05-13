// server_windows.c
// gcc server_windows.c -o server_windows.exe -lws2_32

#define _WIN32_WINNT 0x0601

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#pragma comment(lib, "ws2_32.lib")

#define HOST "0.0.0.0"
#define PORT 5000

typedef struct {
    SOCKET src;
    SOCKET dst;
} RelayArgs;

int send_packet(SOCKET sock, const uint8_t *data, uint32_t length) {
    uint32_t net_len = htonl(length);

    if (send(sock, (const char *)&net_len, sizeof(net_len), 0) != sizeof(net_len)) {
        return -1;
    }

    uint32_t total = 0;

    while (total < length) {
        int sent = send(sock,
                        (const char *)data + total,
                        length - total,
                        0);

        if (sent <= 0) {
            return -1;
        }

        total += sent;
    }

    return 0;
}

int recv_exact(SOCKET sock, uint8_t *buffer, uint32_t size) {
    uint32_t total = 0;

    while (total < size) {
        int received = recv(sock,
                            (char *)buffer + total,
                            size - total,
                            0);

        if (received <= 0) {
            return -1;
        }

        total += received;
    }

    return 0;
}

uint8_t *recv_packet(SOCKET sock, uint32_t *out_length) {
    uint32_t net_len;

    if (recv_exact(sock, (uint8_t *)&net_len, sizeof(net_len)) < 0) {
        return NULL;
    }

    uint32_t length = ntohl(net_len);

    uint8_t *buffer = (uint8_t *)malloc(length);

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

DWORD WINAPI forward_thread(LPVOID arg) {
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

    shutdown(args->src, SD_BOTH);
    shutdown(args->dst, SD_BOTH);

    closesocket(args->src);
    closesocket(args->dst);

    free(args);

    return 0;
}

void relay(SOCKET a, SOCKET b) {
    HANDLE t1, t2;

    RelayArgs *args1 = (RelayArgs *)malloc(sizeof(RelayArgs));
    RelayArgs *args2 = (RelayArgs *)malloc(sizeof(RelayArgs));

    args1->src = a;
    args1->dst = b;

    args2->src = b;
    args2->dst = a;

    t1 = CreateThread(NULL,
                      0,
                      forward_thread,
                      args1,
                      0,
                      NULL);

    t2 = CreateThread(NULL,
                      0,
                      forward_thread,
                      args2,
                      0,
                      NULL);

    CloseHandle(t1);
    CloseHandle(t2);
}

int main() {
    WSADATA wsa;

    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("WSAStartup failed\n");
        return 1;
    }

    SOCKET server_fd;
    struct sockaddr_in server_addr;

    SOCKET waiting[2];
    int waiting_count = 0;

    server_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);

    if (server_fd == INVALID_SOCKET) {
        printf("socket failed\n");
        WSACleanup();
        return 1;
    }

    BOOL opt = TRUE;

    setsockopt(server_fd,
               SOL_SOCKET,
               SO_REUSEADDR,
               (const char *)&opt,
               sizeof(opt));

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd,
             (struct sockaddr *)&server_addr,
             sizeof(server_addr)) == SOCKET_ERROR) {

        printf("bind failed\n");

        closesocket(server_fd);
        WSACleanup();

        return 1;
    }

    if (listen(server_fd, SOMAXCONN) == SOCKET_ERROR) {
        printf("listen failed\n");

        closesocket(server_fd);
        WSACleanup();

        return 1;
    }

    printf("Server running at %s:%d\n", HOST, PORT);

    while (1) {
        struct sockaddr_in client_addr;
        int addr_len = sizeof(client_addr);

        SOCKET client_fd = accept(server_fd,
                                  (struct sockaddr *)&client_addr,
                                  &addr_len);

        if (client_fd == INVALID_SOCKET) {
            printf("accept failed\n");
            continue;
        }

        char ip[INET_ADDRSTRLEN];

        inet_ntop(AF_INET,
                  &client_addr.sin_addr,
                  ip,
                  sizeof(ip));

        printf("Connected: %s:%d\n",
               ip,
               ntohs(client_addr.sin_port));

        waiting[waiting_count++] = client_fd;

        if (waiting_count >= 2) {
            SOCKET a = waiting[0];
            SOCKET b = waiting[1];

            waiting_count = 0;

            printf("Pairing clients\n");

            relay(a, b);
        }
    }

    closesocket(server_fd);
    WSACleanup();

    return 0;
}