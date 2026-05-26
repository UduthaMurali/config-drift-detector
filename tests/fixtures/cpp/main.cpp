// Sample C++ app — test fixture for C++ scanner
#include <cstdlib>
#include <iostream>
#include <string>

int main() {
    // Method 1: std::getenv
    const char* db_url = std::getenv("DATABASE_URL");
    if (!db_url) {
        std::cerr << "DATABASE_URL not set" << std::endl;
        return 1;
    }

    // Method 2: getenv (C-style)
    const char* api_key = getenv("API_KEY");

    // Method 3: with null check guard
    const char* log_level_raw = std::getenv("LOG_LEVEL");
    std::string log_level = log_level_raw ? log_level_raw : "INFO";

    // INTENTIONALLY MISSING from config: SMTP_HOST
    const char* smtp_host = std::getenv("SMTP_HOST");

    std::cout << "App started" << std::endl;
    return 0;
}
