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
} from "recharts";
import { Card, CardContent, Typography, Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";

const ROFRRateChart = ({
  data,
  title = "ROFR Buyback Rate Trends",
  height = 300,
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
              No data available - invalid data format
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Transform data for the chart
  const chartData = data.map((item) => ({
    month: item.month,
    rofrRate: parseFloat(item.rofrRate?.toFixed(2) || 0),
    totalEntries: item.total || 0,
    taken: item.taken || 0,
    passed: item.passed || 0,
    pending: item.pending || 0,
  }));

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
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2" color="error.main">
            ROFR Rate: {data.rofrRate}%
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Total Entries: {data.totalEntries}
          </Typography>
          <Typography variant="body2" color="error.main">
            Taken: {data.taken}
          </Typography>
          <Typography variant="body2" color="success.main">
            Passed: {data.passed}
          </Typography>
          <Typography variant="body2" color="warning.main">
            Pending: {data.pending}
          </Typography>
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
              No data available for the selected period
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ width: "100%", height: height }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
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
              />
              <YAxis
                stroke={theme.palette.text.secondary}
                fontSize={12}
                label={{
                  value: "ROFR Rate (%)",
                  angle: -90,
                  position: "insideLeft",
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="rofrRate"
                stroke={theme.palette.error.main}
                strokeWidth={2}
                dot={{ fill: theme.palette.error.main, strokeWidth: 2, r: 4 }}
                activeDot={{
                  r: 6,
                  stroke: theme.palette.error.main,
                  strokeWidth: 2,
                }}
                name="ROFR Rate (%)"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            ROFR Rate represents the percentage of contracts taken by DVC out of
            total contracts submitted. Higher rates indicate DVC is more
            actively exercising their right of first refusal in that period.
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ROFRRateChart;
