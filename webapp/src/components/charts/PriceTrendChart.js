import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, Typography, Box, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";

const PriceTrendChart = ({
  data,
  title = "Price Trends Over Time",
  height = 400,
  showROFRThreshold = true,
  rofrThreshold = null,
}) => {
  const theme = useTheme();

  // Validate data is an array before processing
  if (!data || !Array.isArray(data)) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {title}
          </Typography>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: height,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No pricing data available - invalid data format
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Transform data for the chart
  const chartData = data.map((item) => ({
    month: item.month,
    averagePrice: parseFloat(item.averagePrice?.toFixed(2) || 0),
    minPrice: parseFloat(item.minPrice?.toFixed(2) || 0),
    maxPrice: parseFloat(item.maxPrice?.toFixed(2) || 0),
    totalEntries: item.total || 0,
    rofrRate: parseFloat(item.rofrRate?.toFixed(2) || 0),
    taken: item.taken || 0,
  }));

  // Calculate average ROFR threshold if not provided
  const calculatedThreshold =
    rofrThreshold ||
    (chartData.length > 0
      ? chartData
          .filter((d) => d.taken > 0)
          .reduce((sum, d) => sum + d.averagePrice, 0) /
        Math.max(chartData.filter((d) => d.taken > 0).length, 1)
      : 0);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          sx={{
            backgroundColor: "white",
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 1,
            p: 2,
            boxShadow: theme.shadows[3],
            minWidth: 200,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2" color="primary.main">
            Avg Price: ${data.averagePrice}/point
          </Typography>
          {data.minPrice > 0 && (
            <Typography variant="body2" color="success.main">
              Min Price: ${data.minPrice}/point
            </Typography>
          )}
          {data.maxPrice > 0 && (
            <Typography variant="body2" color="error.main">
              Max Price: ${data.maxPrice}/point
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            Total Contracts: {data.totalEntries}
          </Typography>
          <Typography variant="body2" color="warning.main">
            ROFR Rate: {data.rofrRate}%
          </Typography>
          {data.taken > 0 && (
            <Typography variant="body2" color="error.main">
              Contracts Taken: {data.taken}
            </Typography>
          )}
        </Box>
      );
    }
    return null;
  };

  if (data.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {title}
          </Typography>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: height,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No pricing data available for the selected period
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const minPrice = Math.min(
    ...chartData.map((d) => d.minPrice).filter((p) => p > 0),
  );
  const maxPrice = Math.max(...chartData.map((d) => d.maxPrice));
  const avgPrice =
    chartData.reduce((sum, d) => sum + d.averagePrice, 0) / chartData.length;

  return (
    <Card>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography variant="h6">{title}</Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Chip
              label={`Avg: $${avgPrice.toFixed(2)}`}
              size="small"
              color="primary"
              variant="outlined"
            />
            {minPrice > 0 && (
              <Chip
                label={`Min: $${minPrice.toFixed(2)}`}
                size="small"
                color="success"
                variant="outlined"
              />
            )}
            <Chip
              label={`Max: $${maxPrice.toFixed(2)}`}
              size="small"
              color="secondary"
              variant="outlined"
            />
          </Box>
        </Box>

        <Box sx={{ width: "100%", height: height }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 20,
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={theme.palette.divider}
              />
              <XAxis
                dataKey="month"
                stroke={theme.palette.text.secondary}
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis
                stroke={theme.palette.text.secondary}
                fontSize={12}
                label={{
                  value: "Price per Point ($)",
                  angle: -90,
                  position: "insideLeft",
                }}
                domain={["dataMin - 10", "dataMax + 10"]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />

              {/* Reference line for ROFR threshold */}
              {showROFRThreshold && calculatedThreshold > 0 && (
                <ReferenceLine
                  y={calculatedThreshold}
                  stroke={theme.palette.warning.main}
                  strokeDasharray="5 5"
                  label={{ value: "Avg ROFR Threshold", position: "topRight" }}
                />
              )}

              {/* Price range area */}
              {chartData.some((d) => d.minPrice > 0 && d.maxPrice > 0) && (
                <>
                  <Line
                    type="monotone"
                    dataKey="maxPrice"
                    stroke={theme.palette.error.light}
                    strokeWidth={1}
                    dot={false}
                    name="Max Price"
                    strokeDasharray="2 2"
                  />
                  <Line
                    type="monotone"
                    dataKey="minPrice"
                    stroke={theme.palette.success.light}
                    strokeWidth={1}
                    dot={false}
                    name="Min Price"
                    strokeDasharray="2 2"
                  />
                </>
              )}

              {/* Average price line */}
              <Line
                type="monotone"
                dataKey="averagePrice"
                stroke={theme.palette.primary.main}
                strokeWidth={3}
                dot={{ fill: theme.palette.primary.main, strokeWidth: 2, r: 4 }}
                activeDot={{
                  r: 6,
                  stroke: theme.palette.primary.main,
                  strokeWidth: 2,
                }}
                name="Average Price"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>

        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Price trends show the movement of DVC contract prices over time. The
            dashed line represents the estimated ROFR threshold - contracts
            priced below this line have a higher likelihood of being bought back
            by DVC.
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PriceTrendChart;
