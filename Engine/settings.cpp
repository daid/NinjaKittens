#include <stdio.h>

#include "settings.h"

#define STRINGIFY(_s) #_s
#define SETTING(name, default) do { _index.push_back(_ConfigSettingIndex(STRINGIFY(name), &name)); name = (default); } while(0)
#define SETTING2(name, altName) _index.push_back(_ConfigSettingIndex(STRINGIFY(name), &name)); _index.push_back(_ConfigSettingIndex(STRINGIFY(altName), &name))

ConfigSettings::ConfigSettings()
{
    SETTING(cutPathOffset, 2000);
    SETTING(cutFeedrate, 10 * 60);
    SETTING(travelHeight, 5000);
    SETTING(travelFeedrate, 150 * 60);
    SETTING(cutDepth, 5000);
    SETTING(cutDepthStep, 1000);
    SETTING(engravePathOffset, 2000);
    SETTING(engraveDepth, 1000);
    SETTING(tabWidth, 5000);
    SETTING(tabDepth, 4000);
    SETTING(minTabDistance, 50000);
    SETTING(maxTabDistance, 150000);
}

#undef STRINGIFY
#undef SETTING

bool ConfigSettings::setSetting(const char* key, const char* value)
{
    for(unsigned int n=0; n < _index.size(); n++)
    {
        if (strcasecmp(key, _index[n].key) == 0)
        {
            *_index[n].ptr = atoi(value);
            return true;
        }
    }
    if (strcasecmp(key, "startCode") == 0)
    {
        this->startCode = value;
        return true;
    }
    if (strcasecmp(key, "endCode") == 0)
    {
        this->endCode = value;
        return true;
    }
    return false;
}
