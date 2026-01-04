import React, { useState } from 'react';

/**
 * Simple Chart Components for API Usage
 * No external dependencies - pure React
 */

interface BarChartProps {
    data: { label: string; value: number }[];
    height?: number;
    color?: string;
}

export const BarChart: React.FC<BarChartProps> = ({
    data,
    height = 200,
    color = '#8b5cf6'
}) => {
    const maxValue = Math.max(...data.map(d => d.value), 1);

    return (
        <div style={{ height, display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            {data.map((item, i) => (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div
                        style={{
                            width: '100%',
                            height: `${(item.value / maxValue) * 100}%`,
                            background: `linear-gradient(180deg, ${color}, ${color}88)`,
                            borderRadius: '4px 4px 0 0',
                            minHeight: '4px',
                            transition: 'height 0.3s ease',
                        }}
                    />
                    <span style={{ fontSize: '11px', color: '#94a3b8', marginTop: '8px' }}>
                        {item.label}
                    </span>
                </div>
            ))}
        </div>
    );
};

interface LineChartProps {
    data: number[];
    labels?: string[];
    height?: number;
    color?: string;
}

export const LineChart: React.FC<LineChartProps> = ({
    data,
    labels,
    height = 200,
    color = '#8b5cf6'
}) => {
    const maxValue = Math.max(...data, 1);
    const minValue = Math.min(...data, 0);
    const range = maxValue - minValue || 1;

    const points = data.map((value, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 100 - ((value - minValue) / range) * 100;
        return `${x},${y}`;
    }).join(' ');

    return (
        <div style={{ height, position: 'relative' }}>
            <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{ width: '100%', height: '100%' }}
            >
                {/* Grid lines */}
                {[0, 25, 50, 75, 100].map(y => (
                    <line
                        key={y}
                        x1="0"
                        y1={y}
                        x2="100"
                        y2={y}
                        stroke="rgba(255,255,255,0.05)"
                        strokeWidth="0.5"
                    />
                ))}

                {/* Area fill */}
                <polygon
                    points={`0,100 ${points} 100,100`}
                    fill={`${color}20`}
                />

                {/* Line */}
                <polyline
                    points={points}
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                />

                {/* Dots */}
                {data.map((value, i) => {
                    const x = (i / (data.length - 1)) * 100;
                    const y = 100 - ((value - minValue) / range) * 100;
                    return (
                        <circle
                            key={i}
                            cx={x}
                            cy={y}
                            r="3"
                            fill={color}
                            vectorEffect="non-scaling-stroke"
                        />
                    );
                })}
            </svg>

            {/* Labels */}
            {labels && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
                    {labels.map((label, i) => (
                        <span key={i} style={{ fontSize: '11px', color: '#94a3b8' }}>
                            {label}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

interface DonutChartProps {
    data: { label: string; value: number; color: string }[];
    size?: number;
}

export const DonutChart: React.FC<DonutChartProps> = ({ data, size = 150 }) => {
    const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
    let currentAngle = -90;

    const getArc = (startAngle: number, endAngle: number, radius: number, innerRadius: number) => {
        const start = ((startAngle * Math.PI) / 180);
        const end = ((endAngle * Math.PI) / 180);
        const x1 = 50 + radius * Math.cos(start);
        const y1 = 50 + radius * Math.sin(start);
        const x2 = 50 + radius * Math.cos(end);
        const y2 = 50 + radius * Math.sin(end);
        const x3 = 50 + innerRadius * Math.cos(end);
        const y3 = 50 + innerRadius * Math.sin(end);
        const x4 = 50 + innerRadius * Math.cos(start);
        const y4 = 50 + innerRadius * Math.sin(start);
        const largeArc = endAngle - startAngle > 180 ? 1 : 0;

        return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4} Z`;
    };

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <svg viewBox="0 0 100 100" style={{ width: size, height: size }}>
                {data.map((item, i) => {
                    const angle = (item.value / total) * 360;
                    const startAngle = currentAngle;
                    currentAngle += angle;
                    return (
                        <path
                            key={i}
                            d={getArc(startAngle, currentAngle, 45, 30)}
                            fill={item.color}
                        />
                    );
                })}
            </svg>
            <div>
                {data.map((item, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: item.color }} />
                        <span style={{ color: '#fff', fontSize: '13px' }}>{item.label}</span>
                        <span style={{ color: '#94a3b8', fontSize: '13px', marginLeft: 'auto' }}>
                            {Math.round((item.value / total) * 100)}%
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Usage Stats Component
interface UsageStatsProps {
    dailyData?: number[];
    riskBreakdown?: { low: number; medium: number; high: number; critical: number };
}

export const UsageStats: React.FC<UsageStatsProps> = ({
    dailyData = [120, 180, 150, 200, 175, 220, 190],
    riskBreakdown = { low: 45, medium: 30, high: 20, critical: 5 }
}) => {
    const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '16px',
                padding: '24px',
                border: '1px solid rgba(255,255,255,0.1)',
            }}>
                <h3 style={{ color: '#fff', marginBottom: '20px', fontSize: '16px' }}>
                    Daily Requests
                </h3>
                <BarChart
                    data={dailyData.map((value, i) => ({ label: weekDays[i], value }))}
                    height={180}
                />
            </div>

            <div style={{
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '16px',
                padding: '24px',
                border: '1px solid rgba(255,255,255,0.1)',
            }}>
                <h3 style={{ color: '#fff', marginBottom: '20px', fontSize: '16px' }}>
                    Risk Distribution
                </h3>
                <DonutChart
                    data={[
                        { label: 'Low', value: riskBreakdown.low, color: '#22c55e' },
                        { label: 'Medium', value: riskBreakdown.medium, color: '#eab308' },
                        { label: 'High', value: riskBreakdown.high, color: '#f97316' },
                        { label: 'Critical', value: riskBreakdown.critical, color: '#ef4444' },
                    ]}
                />
            </div>
        </div>
    );
};

export default UsageStats;
