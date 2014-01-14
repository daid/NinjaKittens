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
    Polygons cutLines;
    Polygons engraveLines;
    
    void readFromStdin()
    {
        int polygonCount;
        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
        {
            int pointCount;
            scanf("%i", &pointCount);
            PolygonRef poly = cutPolygons.newPoly();
            for(int i=0; i<pointCount; i++)
            {
                int x, y;
                scanf("%i %i", &x, &y);
                poly.add(Point(x, y));
            }
        }

        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
        {
            int pointCount;
            scanf("%i", &pointCount);
            PolygonRef poly = engravePolygons.newPoly();
            for(int i=0; i<pointCount; i++)
            {
                int x, y;
                scanf("%i %i", &x, &y);
                poly.add(Point(x, y));
            }
        }

        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
        {
            int pointCount;
            scanf("%i", &pointCount);
            PolygonRef poly = cutLines.newPoly();
            for(int i=0; i<pointCount; i++)
            {
                int x, y;
                scanf("%i %i", &x, &y);
                poly.add(Point(x, y));
            }
        }

        scanf("%i", &polygonCount);
        for(int n=0; n<polygonCount; n++)
        {
            int pointCount;
            scanf("%i", &pointCount);
            PolygonRef poly = engraveLines.newPoly();
            for(int i=0; i<pointCount; i++)
            {
                int x, y;
                scanf("%i %i", &x, &y);
                poly.add(Point(x, y));
            }
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
            center.push_back(parts[n][0].centerOfMass());
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

class PolygonDetails
{
public:
    int length;
    vector<int> offset;
    vector<int> distance;
    vector<double> cosAngle;

    PolygonDetails(PolygonRef poly)
    {
        Point p0 = poly[poly.size()-1];
        length = 0;
        for(unsigned int n=0; n<poly.size(); n++)
        {
            Point p1 = poly[n];
            Point p2 = poly[(n + 1) % poly.size()];
            int dist = vSize(p0 - p1);
            if (n > 0)
                length += dist;
            distance.push_back(dist);
            cosAngle.push_back(double(dot(p1 - p0, crossZ(p1 - p2))) / double(vSize(p1 - p0)) / double(vSize(p1 - p2)));
            offset.push_back(length);
            p0 = p1;
        }
    }
    
    double maxCosAngle(int minOffset, int maxOffset)
    {
        double maxCos = 0;
        for(unsigned int n=0; n<offset.size(); n++)
        {
            if ((offset[n] >= minOffset && offset[n] <= maxOffset) || (offset[n] - length >= minOffset && offset[n] - length <= maxOffset))
            {
                maxCos = std::max(maxCos, fabs(cosAngle[n]));
            }
        }
        return maxCos;
    }
};

class HoldingTabProcessor
{
    Polygon poly;
    vector<int> depthList;
    int tabWidth;
public:
    int bestTabOffset(PolygonDetails& details, int minOffset, int maxOffset)
    {
        int offset = minOffset;
        if (maxOffset > details.length && minOffset < details.length)
            maxOffset = details.length;
        while(offset < maxOffset && details.maxCosAngle(offset - tabWidth * 0.5, offset + tabWidth * 1.5) > 0.4)
            offset += tabWidth / 2;
        if (offset >= maxOffset)
            return (minOffset + maxOffset) / 2;
        return offset;
    }

    HoldingTabProcessor(PolygonRef p, int cutDepth, int tabWidth, int tabDepth, int minDistance, int maxDistance)
    : tabWidth(tabWidth)
    {
        PolygonDetails details(p);
        if (cutDepth < tabDepth || details.length < minDistance)
        {
            for(unsigned int n=0; n<p.size(); n++)
            {
                poly.add(p[n]);
                depthList.push_back(cutDepth);
            }
            return;
        }
        
        int totalLength = details.length;
        vector<int> switchPoint;
        
        int length = bestTabOffset(details, 0, maxDistance - minDistance);
        switchPoint.push_back(length);
        while(length < totalLength)
        {
            length += tabWidth;
            switchPoint.push_back(length);
            length = bestTabOffset(details, length + minDistance, length + maxDistance);
            switchPoint.push_back(length);
        }
        
        length = 0;
        bool inTab = false;
        Point p0 = p[0];
        unsigned int spIdx = 0;
        for(unsigned int n=0; n<p.size(); n++)
        {
            int dist = vSize(p0 - p[n]);

            while(spIdx < switchPoint.size() && length + dist > switchPoint[spIdx])
            {
                int offset = (switchPoint[spIdx] - length);
                Point switchPos = p0 + (p[n] - p0) * offset / dist;
                poly.add(switchPos);
                depthList.push_back(inTab ? tabDepth: cutDepth);
                inTab = !inTab;
                poly.add(switchPos);
                depthList.push_back(inTab ? tabDepth: cutDepth);
                
                spIdx++;
            }
            length += dist;

            poly.add(p[n]);
            depthList.push_back(inTab ? tabDepth: cutDepth);
            p0 = p[n];
        }
    }
    
    void write(GCodeExport& gcode, int feedrate)
    {
        gcode.addMove(poly[0], feedrate);
        gcode.setZ(-depthList[0]);
        gcode.addMove(poly[0], feedrate);
        for(unsigned int i=1; i<poly.size(); i++)
        {
            gcode.setZ(-depthList[i]);
            gcode.addMove(poly[i], feedrate);
        }
        gcode.setZ(-depthList[0]);
        gcode.addMove(poly[0], feedrate);
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
        gcode.addCode(config.startCode);
    }
    
    void process()
    {
        {
            Polygons paths = drawing.engraveLines;
            processPart(paths, config.engraveDepth, false);
        }

        {
            Polygons paths = drawing.engravePolygons.offset(-config.engravePathOffset);
            vector<Polygons> parts = paths.splitIntoParts();
            PartOrderOptimizer order(gcode.getPositionXY(), parts);
            for(unsigned int n=0; n<parts.size(); n++)
            {
                processPart(parts[order[n]], config.engraveDepth, true);
            }
        }

        {
            Polygons paths = drawing.cutLines;
            processPart(paths, config.cutDepth, false);
        }

        {
            Polygons paths = drawing.cutPolygons.offset(config.cutPathOffset);
            vector<Polygons> parts = paths.splitIntoParts();
            PartOrderOptimizer order(gcode.getPositionXY(), parts);
            for(unsigned int n=0; n<parts.size(); n++)
                processPart(parts[order[n]], config.cutDepth, true);
        }

        gcode.addCode(config.endCode);
    }
    
    void processPart(Polygons paths, int totalDepth, bool closed)
    {
        int cutOrder[paths.size()];
        for(unsigned int n=0; n<paths.size(); n++)
            cutOrder[n] = n;
        
        //Bubble sort, I know, I suck.
        for(unsigned int m=0; m<paths.size(); m++)
        for(unsigned int n=1; n<paths.size(); n++)
        {
            if (!paths[cutOrder[n]].orientation() && paths[cutOrder[n-1]].orientation())
            {
                int tmp = cutOrder[n];
                cutOrder[n] = cutOrder[n-1];
                cutOrder[n-1] = tmp;
            }else{
                double score = 0;
                score += fabs(paths[cutOrder[n]].area()) - abs(paths[cutOrder[n-1]].area());
                
                Point p0 = gcode.getPositionXY();
                if (n > 1)
                    p0 = paths[cutOrder[n-2]].centerOfMass();

                score += vSize(paths[cutOrder[n]].centerOfMass() - p0);
                score -= vSize(paths[cutOrder[n-1]].centerOfMass() - p0);

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
            gcode.addMove(paths[n][0], config.travelFeedrate);
            int depth = 0;
            do
            {
                depth += config.cutDepthStep;
                if (depth > totalDepth)
                    depth = totalDepth;
                if (closed)
                {
                    HoldingTabProcessor holdingTabProcessor(paths[n], depth, config.tabWidth, config.tabDepth, config.minTabDistance, config.maxTabDistance);
                    holdingTabProcessor.write(gcode, config.cutFeedrate);
                }else{
                    gcode.setZ(config.travelHeight);
                    gcode.addMove(gcode.getPositionXY(), config.travelFeedrate);
                    gcode.addMove(paths[n][0], config.travelFeedrate);
                    gcode.setZ(-depth);
                    for(unsigned int i=0; i<paths[n].size(); i++)
                        gcode.addMove(paths[n][i], config.cutFeedrate);
                }
            }while(depth < totalDepth);
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
