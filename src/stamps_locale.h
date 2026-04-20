// StaMPS Windows-port: C-locale pin for deterministic numeric I/O.
// Every main() in src/ begins with STAMPS_PIN_C_LOCALE() so output floats
// use '.' as decimal separator regardless of user's OS locale, and input
// >> float parses identically on every platform.

#ifndef STAMPS_LOCALE_H
#define STAMPS_LOCALE_H

#include <clocale>
#include <iostream>
#include <locale>

inline void stamps_pin_c_locale() {
    std::setlocale(LC_ALL, "C");
    std::cin.imbue(std::locale::classic());
    std::cout.imbue(std::locale::classic());
    std::cerr.imbue(std::locale::classic());
}

#define STAMPS_PIN_C_LOCALE() stamps_pin_c_locale()

#endif
