#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_USERS 5

typedef struct {
    char username[32];
    char password[32];
    int age;
} User;

User *users[MAX_USERS];
int user_count = 0;

// ---------------------------
// Register a new user
// ---------------------------
void register_user() {
    if (user_count >= MAX_USERS) {
        printf("User limit reached.\n");
        return;
    }

    User *u = (User *)malloc(sizeof(User));
    if (!u) {
        printf("Memory allocation failed.\n");
        return;
    }

    printf("Enter username: ");
    gets(u->username);              // ❌ STACK OVERFLOW

    printf("Enter password: ");
    scanf("%s", u->password);       // ❌ STACK OVERFLOW (unbounded)

    printf("Enter age: ");
    scanf("%d", &u->age);

    users[user_count++] = u;
    printf("User registered successfully.\n");
}

// ---------------------------
// Change password
// ---------------------------
void change_password() {
    char temp[16];

    printf("Enter new password: ");
    gets(temp);                      // ❌ STACK OVERFLOW

    if (user_count == 0) {
        printf("No users found.\n");
        return;
    }

    strcpy(users[0]->password, temp);  // ❌ STACK OVERFLOW
}

// ---------------------------
// Export usernames to file
// ---------------------------
void export_users() {
    FILE *fp = fopen("users.txt", "w");
    if (!fp) {
        printf("Failed to open file.\n");
        return;
    }

    char *buffer = (char *)malloc(64);
    if (!buffer) return;

    for (int i = 0; i < user_count; i++) {
        strcpy(buffer, users[i]->username);   // ❌ HEAP OVERFLOW
        strcat(buffer, "\n");                 // ❌ HEAP OVERFLOW
        fputs(buffer, fp);
    }

    fclose(fp);
    free(buffer);
}

// ---------------------------
// Calculate total age
// ---------------------------
void calculate_total_age() {
    int total = 0;

    for (int i = 0; i < user_count; i++) {
        total += users[i]->age;   // ⚠ Possible INTEGER OVERFLOW
    }

    printf("Total age: %d\n", total);
}

// ---------------------------
// Delete user
// ---------------------------
void delete_user() {
    if (user_count == 0) {
        printf("No users to delete.\n");
        return;
    }

    free(users[0]);
    users[0] = NULL;

    printf("User deleted.\n");

    printf("Accessing deleted user...\n");
    printf("Username: %s\n", users[0]->username);  // ❌ NULL DEREFERENCE
}

// ---------------------------
// Main Menu
// ---------------------------
int main() {
    int choice;

    while (1) {
        printf("\n1. Register\n2. Change Password\n3. Export\n4. Total Age\n5. Delete\n6. Exit\n");
        printf("Choice: ");
        scanf("%d", &choice);

        switch (choice) {
            case 1: register_user(); break;
            case 2: change_password(); break;
            case 3: export_users(); break;
            case 4: calculate_total_age(); break;
            case 5: delete_user(); break;
            case 6: exit(0);
            default: printf("Invalid choice.\n");
        }
    }

    return 0;
}
