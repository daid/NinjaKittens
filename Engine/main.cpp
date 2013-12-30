#include <stdio.h>

#include "utils/polygon.h"
#include "gcodeExport.h"
#include "settings.h"

class Drawing
{
public:
    Polygons cutPolygons;
    
    void readFromStdin()
    {
        int cutPolygonCount;
        scanf("%i", &cutPolygonCount);
        for(int n=0; n<cutPolygonCount; n++)
        {
            int pointCount;
            scanf("%i", &pointCount);
            ClipperLib::Path poly;
            for(int i=0; i<pointCount; i++)
            {
                int x, y;
                scanf("%i %i", &x, &y);
                poly.push_back(Point(x, y));
            }
            cutPolygons.add(poly);
        }
        
        cutPolygons = cutPolygons.processEvenOdd();
    }
};

class CuttingProcessor
{
public:
    Drawing& drawing;
    ConfigSettings& config;
    GCodeExport gcode;
    
    CuttingProcessor(Drawing& drawing, ConfigSettings& config)
    : drawing(drawing), config(config)
    {
    }
    
    void process()
    {
        Polygons paths = drawing.cutPolygons.offset(config.cutPathOffset);
        for(unsigned int n=0; n<paths.size(); n++)
        {
            gcode.setZ(config.travelHeight);
            gcode.addMove(gcode.getPositionXY(), config.travelFeedrate);
            gcode.addMove(paths[n][0], config.travelFeedrate);
            int depth = 0;
            do
            {
                depth -= config.cutDepthStep;
                if (depth < -config.cutDepth)
                    depth = -config.cutDepth;
                gcode.setZ(depth);
                gcode.addMove(gcode.getPositionXY(), config.cutFeedrate);
                for(unsigned int i=1; i<paths[n].size(); i++)
                {
                    gcode.addMove(paths[n][i], config.cutFeedrate);
                }
                gcode.addMove(paths[n][0], config.cutFeedrate);
            }while(depth > -config.cutDepth);
        }
    }
};

int main(int argc, char** argv)
{
    ConfigSettings config;
    Drawing drawing;
    
    for(int argn = 1; argn < argc; argn++)
    {
        char* str = argv[argn];
        if (str[0] == '-')
        {
            for(str++; *str; str++)
            {
                switch(*str)
                {
                case 'r':
                    drawing.readFromStdin();
                    break;
                case 's':
                    {
                        argn++;
                        char* valuePtr = strchr(argv[argn], '=');
                        if (valuePtr)
                        {
                            *valuePtr++ = '\0';
                            
                            if (!config.setSetting(argv[argn], valuePtr))
                                fprintf(stderr, "Setting not found: %s %s\n", argv[argn], valuePtr);
                        }
                    }
                    break;
                case 'p':
                    {
                        CuttingProcessor processor(drawing, config);
                        processor.process();
                    }
                    break;
                }
            }
        }
    }
}
