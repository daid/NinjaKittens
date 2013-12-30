/** Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License */
#ifndef GCODEEXPORT_H
#define GCODEEXPORT_H

#include <stdio.h>

#include "settings.h"
#include "utils/intpoint.h"
#include "utils/polygon.h"

class GCodeExport
{
private:
    Point3 currentPosition;
    int currentSpeed;
    int zPos;
    
public:
    GCodeExport();
    ~GCodeExport();
    
    void setZ(int z);
    
    Point getPositionXY();
    
    int getPositionZ();

    void addComment(const char* comment, ...);

    void addLine(const char* line, ...);
    
    void addDelay(double timeAmount);
    
    void addMove(Point p, int speed);
    
    void addCode(const char* str);
};

#endif//GCODEEXPORT_H
