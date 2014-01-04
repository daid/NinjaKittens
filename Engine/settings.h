#ifndef SETTINGS_H
#define SETTINGS_H

#include "utils/floatpoint.h"
#include <vector>

#define VERSION "0.0"

class _ConfigSettingIndex
{
public:
    const char* key;
    int* ptr;
    
    _ConfigSettingIndex(const char* key, int* ptr) : key(key), ptr(ptr) {}
};

class ConfigSettings
{
private:
    std::vector<_ConfigSettingIndex> _index;
public:
    int cutPathOffset;
    int cutFeedrate;
    int travelHeight;
    int travelFeedrate;
    int cutDepth;
    int cutDepthStep;
    int engravePathOffset;
    int engraveDepth;
    int tabWidth;
    int tabDepth;
    int minTabDistance;
    int maxTabDistance;
    
    const char* startCode;
    const char* endCode;
    
    ConfigSettings();
    bool setSetting(const char* key, const char* value);
};

#endif//SETTINGS_H
