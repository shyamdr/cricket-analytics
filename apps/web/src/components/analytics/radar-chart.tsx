"use client";

interface RadarAxis {
  label: string;
  value: number;
  max: number;
}

interface RadarChartProps {
  axes: RadarAxis[];
  color?: string;
  size?: number;
}

export function RadarChart({ axes, color = "#3b82f6", size = 180 }: RadarChartProps) {
  if (axes.length < 3) return null;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 24;
  const angleStep = (2 * Math.PI) / axes.length;
  const levels = [0.25, 0.5, 0.75, 1.0];

  const getPoint = (index: number, ratio: number) => {
    const angle = angleStep * index - Math.PI / 2;
    return {
      x: cx + radius * ratio * Math.cos(angle),
      y: cy + radius * ratio * Math.sin(angle),
    };
  };

  // Data polygon
  const dataPoints = axes.map((a, i) => {
    const ratio = Math.min(a.value / a.max, 1);
    return getPoint(i, ratio);
  });
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {/* Grid levels */}
      {levels.map((level) => {
        const pts = axes.map((_, i) => getPoint(i, level));
        const path = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        return <path key={level} d={path} fill="none" stroke="currentColor" strokeOpacity={0.1} strokeWidth={1} />;
      })}

      {/* Axis lines */}
      {axes.map((_, i) => {
        const p = getPoint(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="currentColor" strokeOpacity={0.1} strokeWidth={1} />;
      })}

      {/* Data polygon */}
      <path d={dataPath} fill={color} fillOpacity={0.15} stroke={color} strokeWidth={2} />

      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill={color} />
      ))}

      {/* Labels */}
      {axes.map((a, i) => {
        const p = getPoint(i, 1.18);
        const anchor = p.x < cx - 5 ? "end" : p.x > cx + 5 ? "start" : "middle";
        return (
          <text key={i} x={p.x} y={p.y} textAnchor={anchor} dominantBaseline="central"
            className="fill-muted-foreground text-[9px]">
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
