#include <stdio.h>

#include "utils/polygon.h"
#include "gcodeExport.h"
#include "settings.h"
#include "infill.h"

class Drawing
{
public:
    Polygons cutPolygons;
    Polygons engravePolygons;
    
    void readFromStdin()
    {
        int polygonCount;
        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
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

        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
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
            engravePolygons.add(poly);
        }
        
        cutPolygons = cutPolygons.processEvenOdd();
        engravePolygons = engravePolygons.processEvenOdd();
    }
};

class PartOrderOptimizer
{
    vector<Polygons>& parts;
    vector<int> order;
public:
    
    PartOrderOptimizer(Point startPoint, vector<Polygons>& parts)
    : parts(parts)
    {
        vector<bool> picked;
        vector<Point> center;
        for(unsigned int n=0; n<parts.size(); n++)
        {
            center.push_back(parts[n].centerOfMass(0));
            picked.push_back(false);
        }
        
        Point p0 = startPoint;
        for(unsigned int cnt=0; cnt<parts.size(); cnt++)
        {
            int best = -1;
            for(unsigned int n=0; n<parts.size(); n++)
            {
                if (picked[n]) continue;
                if (best == -1 || vSize2f(center[n] - p0) < vSize2f(center[best] - p0))
                    best = n;
            }
            picked[best] = true;
            order.push_back(best);
            p0 = center[best];
        }
    }
    
    int operator[] (int idx)
    {
        return order[idx];
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
        {
            Polygons paths = drawing.engravePolygons.offset(-config.cutPathOffset);
            vector<Polygons> parts = paths.splitIntoParts();
            PartOrderOptimizer order(gcode.getPositionXY(), parts);
            for(unsigned int n=0; n<parts.size(); n++)
            {
                processPart(parts[order[n]], config.engraveDepth);
            }
        }

        {
            Polygons paths = drawing.cutPolygons.offset(config.cutPathOffset);
            vector<Polygons> parts = paths.splitIntoParts();
            PartOrderOptimizer order(gcode.getPositionXY(), parts);
            for(unsigned int n=0; n<parts.size(); n++)
                processPart(parts[order[n]], config.cutDepth);
        }
    }
    
    void processPart(Polygons paths, int totalDepth)
    {
        int cutOrder[paths.size()];
        for(unsigned int n=0; n<paths.size(); n++)
            cutOrder[n] = n;
        
        //Bubble sort, I know, I suck.
        for(unsigned int m=0; m<paths.size(); m++)
        for(unsigned int n=1; n<paths.size(); n++)
        {
            if (!paths.orientation(cutOrder[n]) && paths.orientation(cutOrder[n-1]))
            {
                int tmp = cutOrder[n];
                cutOrder[n] = cutOrder[n-1];
                cutOrder[n-1] = tmp;
            }else{
                double score = 0;
                score += paths.area(cutOrder[n]) - paths.area(cutOrder[n-1]);
                
                Point p0 = gcode.getPositionXY();
                if (n > 1)
                    p0 = paths.centerOfMass(cutOrder[n-2]);

                score += vSize(paths.centerOfMass(cutOrder[n]) - p0);
                score -= vSize(paths.centerOfMass(cutOrder[n-1]) - p0);

                if (score < 0)
                {
                    int tmp = cutOrder[n];
                    cutOrder[n] = cutOrder[n-1];
                    cutOrder[n-1] = tmp;
                }
            }
        }
        
        for(unsigned int idx=0; idx<paths.size(); idx++)
        {
            unsigned int n = cutOrder[idx];
            gcode.setZ(config.travelHeight);
            gcode.addMove(gcode.getPositionXY(), config.travelFeedrate);
            int startIdx = 0;
            for(unsigned int i=1; i<paths[n].size(); i++)
                if (vSize2(paths[n][i] - gcode.getPositionXY()) < vSize2(paths[n][startIdx] - gcode.getPositionXY()))
                    startIdx = i;
            gcode.addMove(paths[n][startIdx], config.travelFeedrate);
            int depth = 0;
            do
            {
                depth -= config.cutDepthStep;
                if (depth < -totalDepth)
                    depth = -totalDepth;
                gcode.setZ(depth);
                gcode.addMove(gcode.getPositionXY(), config.cutFeedrate);
                for(unsigned int i=1; i<paths[n].size(); i++)
                {
                    gcode.addMove(paths[n][(startIdx+i)%paths[n].size()], config.cutFeedrate);
                }
                gcode.addMove(paths[n][startIdx], config.cutFeedrate);
            }while(depth > -totalDepth);
        }
    }

    void processLines(Polygons lines, int totalDepth)
    {
        for(unsigned int idx=0; idx<lines.size(); idx++)
        {
            unsigned int n = idx;
            gcode.setZ(config.travelHeight);
            gcode.addMove(gcode.getPositionXY(), config.travelFeedrate);
            int startIdx = 0;
            for(unsigned int i=1; i<lines[n].size(); i++)
                if (vSize2(lines[n][i] - gcode.getPositionXY()) < vSize2(lines[n][startIdx] - gcode.getPositionXY()))
                    startIdx = i;
            gcode.addMove(lines[n][startIdx], config.travelFeedrate);
            int depth = 0;
            do
            {
                depth -= config.cutDepthStep;
                if (depth < -totalDepth)
                    depth = -totalDepth;
                gcode.setZ(depth);
                gcode.addMove(gcode.getPositionXY(), config.cutFeedrate);
                for(unsigned int i=1; i<lines[n].size(); i++)
                {
                    gcode.addMove(lines[n][(startIdx+i)%lines[n].size()], config.cutFeedrate);
                }
            }while(depth > -totalDepth);
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
