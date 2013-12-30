/** Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License */
#include <stdarg.h>

#include "gcodeExport.h"
#include "settings.h"

#if defined(__APPLE__) && defined(__MACH__)
//On MacOS the file offset functions are always 64bit.
#define off64_t off_t
#define ftello64 ftello
#define fseeko64 fseeko
#endif

GCodeExport::GCodeExport()
: currentPosition(0,0,0)
{
    currentSpeed = 0;
    zPos = 0.0;
}

GCodeExport::~GCodeExport()
{
}

void GCodeExport::setZ(int z)
{
    this->zPos = z;
}

Point GCodeExport::getPositionXY()
{
    return Point(currentPosition.x, currentPosition.y);
}

int GCodeExport::getPositionZ()
{
    return currentPosition.z;
}

void GCodeExport::addComment(const char* comment, ...)
{
    va_list args;
    va_start(args, comment);
    printf(";");
    vprintf(comment, args);
    printf("\n");
    va_end(args);
}

void GCodeExport::addLine(const char* line, ...)
{
    va_list args;
    va_start(args, line);
    vprintf(line, args);
    printf("\n");
    va_end(args);
}

void GCodeExport::addDelay(double timeAmount)
{
    printf("G4 P%d\n", int(timeAmount * 1000));
}

void GCodeExport::addMove(Point p, int speed)
{
    printf("G1");
    
    if (currentSpeed != speed)
    {
        printf(" F%i", speed);
        currentSpeed = speed;
    }
    printf(" X%0.2f Y%0.2f", float(p.X)/1000, float(p.Y)/1000);
    if (zPos != currentPosition.z)
        printf(" Z%0.2f", float(zPos)/1000);
    printf("\n");
    
    currentPosition = Point3(p.X, p.Y, zPos);
}

void GCodeExport::addCode(const char* str)
{
    printf("%s\n", str);
}
