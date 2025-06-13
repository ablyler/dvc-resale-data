import React, { useState, useEffect, useCallback } from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Avatar,
  LinearProgress,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Star as StarIcon,
  CheckCircle as CheckCircleIcon,
} from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { useApi } from "../context/ApiContext";

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
    },
  },
};

const ResortComparison = () => {
  const theme = useTheme();
  const { getResortComparison, getResorts, error, prefetchData } = useApi();

  const [resorts, setResorts] = useState([]);
  const [selectedResorts, setSelectedResorts] = useState([]);
  const [comparisonData, setComparisonData] = useState([]);
  const [loadingData, setLoadingData] = useState(false);
  const [timeRange, setTimeRange] = useState(12);

  useEffect(() => {
    const fetchResorts = async () => {
      try {
        // Prefetch resorts data for better performance
        await prefetchData(["resorts"]);

        const resortsData = await getResorts();
        setResorts(resortsData.data || []);

        // Pre-select popular resorts for initial comparison
        const popularResorts = ["VGF", "BCV", "BWV", "AKV", "RIV"];
        const resortsList = resortsData.data || [];
        const availablePopular = resortsList
          .filter((r) => popularResorts.includes(r))
          .slice(0, 3);

        setSelectedResorts(availablePopular);
      } catch (err) {
        console.error("Error fetching resorts:", err);
      }
    };

    fetchResorts();
  }, [getResorts, prefetchData]);

  const fetchComparisonData = useCallback(async () => {
    if (selectedResorts.length === 0) return;

    setLoadingData(true);
    try {
      // Use optimized batch API call instead of individual requests
      const comparisonResult = await getResortComparison(
        selectedResorts,
        timeRange,
      );

      const processedData = selectedResorts.map((resort) => {
        const resortData = comparisonResult[resort];
        const entries = resortData?.data || [];

        // Calculate statistics
        const totalEntries = entries.length;
        const passedEntries = entries.filter(
          (e) => e.result === "passed",
        ).length;
        const takenEntries = entries.filter((e) => e.result === "taken").length;
        const pendingEntries = entries.filter(
          (e) => e.result === "pending",
        ).length;

        const prices = entries
          .map((e) => e.price_per_point)
          .filter((p) => p > 0);
        const avgPrice =
          prices.length > 0
            ? prices.reduce((sum, p) => sum + p, 0) / prices.length
            : 0;
        const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
        const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;

        const rofrRate =
          totalEntries > 0 ? (takenEntries / totalEntries) * 100 : 0;

        // Calculate trend (last 3 months vs previous 3 months)
        const recentEntries = entries.filter((e) => {
          if (!e.sent_date) return false;
          const date = new Date(e.sent_date);
          const threeMonthsAgo = new Date();
          threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
          return date >= threeMonthsAgo;
        });

        const olderEntries = entries.filter((e) => {
          if (!e.sent_date) return false;
          const date = new Date(e.sent_date);
          const sixMonthsAgo = new Date();
          sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
          const threeMonthsAgo = new Date();
          threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
          return date >= sixMonthsAgo && date < threeMonthsAgo;
        });

        const recentAvgPrice =
          recentEntries.length > 0
            ? recentEntries.reduce(
                (sum, e) => sum + (e.price_per_point || 0),
                0,
              ) / recentEntries.length
            : 0;

        const olderAvgPrice =
          olderEntries.length > 0
            ? olderEntries.reduce(
                (sum, e) => sum + (e.price_per_point || 0),
                0,
              ) / olderEntries.length
            : recentAvgPrice;

        const priceTrend =
          olderAvgPrice > 0
            ? ((recentAvgPrice - olderAvgPrice) / olderAvgPrice) * 100
            : 0;

        // Calculate recent activity (entries in last 3 months)
        const recentActivity = recentEntries.length;

        // Calculate radar chart metrics (0-100 scale)
        const marketActivity = Math.min((recentActivity / 10) * 100, 100); // Scale based on 10+ recent entries = 100%

        const priceStability = Math.max(0, 100 - Math.abs(priceTrend * 2)); // Less price volatility = higher stability

        const rofrSafety = Math.max(0, 100 - rofrRate * 5); // Lower ROFR rate = higher safety

        const liquidityScore = Math.min((totalEntries / 50) * 100, 100); // Scale based on 50+ total entries = 100%

        return {
          resort,
          resortName: resorts.find((r) => r.code === resort)?.name || resort,
          totalEntries,
          passedEntries,
          takenEntries,
          pendingEntries,
          avgPrice,
          minPrice,
          maxPrice,
          rofrRate,
          priceTrend,
          recentActivity,
          marketActivity,
          priceStability,
          rofrSafety,
          liquidityScore,
          data: entries,
        };
      });

      setComparisonData(processedData);
    } catch (err) {
      console.error("Error fetching comparison data:", err);
    } finally {
      setLoadingData(false);
    }
  }, [selectedResorts, timeRange, getResortComparison, resorts]);

  useEffect(() => {
    if (selectedResorts.length > 0) {
      fetchComparisonData();
    }
  }, [selectedResorts, timeRange, fetchComparisonData]);

  const handleResortChange = (event) => {
    const value = event.target.value;
    setSelectedResorts(typeof value === "string" ? value.split(",") : value);
  };

  const ComparisonTable = () => {
    if (comparisonData.length === 0) return null;

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Resort Comparison Summary
          </Typography>

          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Resort</TableCell>
                  <TableCell align="right">Avg Price/Point</TableCell>
                  <TableCell align="right">Price Range</TableCell>
                  <TableCell align="right">ROFR Rate</TableCell>
                  <TableCell align="right">Total Entries</TableCell>
                  <TableCell align="right">Recent Activity</TableCell>
                  <TableCell align="right">Price Trend</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {comparisonData.map((data) => (
                  <TableRow key={data.resort} hover>
                    <TableCell>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Avatar
                          sx={{
                            width: 24,
                            height: 24,
                            fontSize: "0.7rem",
                            bgcolor: "primary.main",
                          }}
                        >
                          {data.resort.charAt(0)}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {data.resort}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {data.resortName}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight="medium">
                        ${data.avgPrice.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        ${data.minPrice.toFixed(0)} - $
                        {data.maxPrice.toFixed(0)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: 1,
                        }}
                      >
                        <Typography variant="body2">
                          {data.rofrRate.toFixed(1)}%
                        </Typography>
                        <Chip
                          size="small"
                          label={
                            data.rofrRate < 5
                              ? "Low"
                              : data.rofrRate < 15
                                ? "Medium"
                                : "High"
                          }
                          color={
                            data.rofrRate < 5
                              ? "success"
                              : data.rofrRate < 15
                                ? "warning"
                                : "error"
                          }
                          variant="outlined"
                        />
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        {data.totalEntries}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        {data.recentActivity}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: 1,
                        }}
                      >
                        {data.priceTrend > 2 ? (
                          <TrendingUpIcon color="success" fontSize="small" />
                        ) : data.priceTrend < -2 ? (
                          <TrendingDownIcon color="error" fontSize="small" />
                        ) : null}
                        <Typography
                          variant="body2"
                          color={
                            data.priceTrend > 2
                              ? "success.main"
                              : data.priceTrend < -2
                                ? "error.main"
                                : "text.primary"
                          }
                        >
                          {data.priceTrend > 0 ? "+" : ""}
                          {data.priceTrend.toFixed(1)}%
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    );
  };

  const PriceComparisonChart = () => {
    if (comparisonData.length === 0) return null;

    const chartData = comparisonData.map((data) => ({
      resort: data.resort,
      avgPrice: data.avgPrice,
      minPrice: data.minPrice,
      maxPrice: data.maxPrice,
    }));

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Price Comparison
          </Typography>

          <Box sx={{ width: "100%", height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="resort" />
                <YAxis
                  label={{
                    value: "Price per Point ($)",
                    angle: -90,
                    position: "insideLeft",
                  }}
                />
                <Tooltip
                  formatter={(value, name) => [`$${value.toFixed(2)}`, name]}
                  labelFormatter={(label) => `Resort: ${label}`}
                />
                <Legend />
                <Bar
                  dataKey="minPrice"
                  fill={theme.palette.success.light}
                  name="Min Price"
                />
                <Bar
                  dataKey="avgPrice"
                  fill={theme.palette.primary.main}
                  name="Avg Price"
                />
                <Bar
                  dataKey="maxPrice"
                  fill={theme.palette.error.light}
                  name="Max Price"
                />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    );
  };

  const ResortScoreCard = () => {
    if (comparisonData.length === 0) return null;

    const radarData = comparisonData.map((data) => ({
      resort: data.resort,
      "Market Activity": data.marketActivity,
      "Price Stability": data.priceStability,
      "ROFR Safety": data.rofrSafety,
      Liquidity: data.liquidityScore,
    }));

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Resort Performance Radar
          </Typography>

          <Box sx={{ width: "100%", height: 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="resort" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                {[
                  "Market Activity",
                  "Price Stability",
                  "ROFR Safety",
                  "Liquidity",
                ].map((metric, index) => (
                  <Radar
                    key={metric}
                    name={metric}
                    dataKey={metric}
                    stroke={theme.palette.primary.main}
                    fill={theme.palette.primary.main}
                    fillOpacity={0.1 + index * 0.1}
                  />
                ))}
                <Tooltip />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </Box>

          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Score ranges from 0-100. Higher scores indicate better performance
              in each category.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  };

  const ResortRecommendations = () => {
    if (comparisonData.length === 0) return null;

    // Calculate overall scores
    const scoredResorts = comparisonData
      .map((data) => ({
        ...data,
        overallScore:
          (data.marketActivity +
            data.priceStability +
            data.rofrSafety +
            data.liquidityScore) /
          4,
      }))
      .sort((a, b) => b.overallScore - a.overallScore);

    const topResort = scoredResorts[0];
    const bestValue = comparisonData.reduce((prev, current) =>
      prev.avgPrice < current.avgPrice && prev.rofrRate < current.rofrRate
        ? prev
        : current,
    );
    const mostActive = comparisonData.reduce((prev, current) =>
      prev.recentActivity > current.recentActivity ? prev : current,
    );

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recommendations
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Box
                sx={{ p: 2, backgroundColor: "success.light", borderRadius: 1 }}
              >
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
                >
                  <StarIcon color="inherit" />
                  <Typography variant="subtitle2" color="success.contrastText">
                    Top Overall
                  </Typography>
                </Box>
                <Typography variant="h6" color="success.contrastText">
                  {topResort.resort}
                </Typography>
                <Typography variant="body2" color="success.contrastText">
                  Score: {topResort.overallScore.toFixed(1)}/100
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box
                sx={{ p: 2, backgroundColor: "primary.light", borderRadius: 1 }}
              >
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
                >
                  <CheckCircleIcon color="inherit" />
                  <Typography variant="subtitle2" color="primary.contrastText">
                    Best Value
                  </Typography>
                </Box>
                <Typography variant="h6" color="primary.contrastText">
                  {bestValue.resort}
                </Typography>
                <Typography variant="body2" color="primary.contrastText">
                  ${bestValue.avgPrice.toFixed(2)}/pt,{" "}
                  {bestValue.rofrRate.toFixed(1)}% ROFR
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box
                sx={{
                  p: 2,
                  backgroundColor: "secondary.light",
                  borderRadius: 1,
                }}
              >
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
                >
                  <TrendingUpIcon color="inherit" />
                  <Typography
                    variant="subtitle2"
                    color="secondary.contrastText"
                  >
                    Most Active
                  </Typography>
                </Box>
                <Typography variant="h6" color="secondary.contrastText">
                  {mostActive.resort}
                </Typography>
                <Typography variant="body2" color="secondary.contrastText">
                  {mostActive.recentActivity} recent entries
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  if (loadingData && comparisonData.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
        }}
      >
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Error loading resort comparison: {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        Resort Comparison
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Compare DVC resorts across key purchasing metrics
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={8}>
              <FormControl fullWidth>
                <InputLabel>Select Resorts to Compare</InputLabel>
                <Select
                  multiple
                  value={selectedResorts}
                  onChange={handleResortChange}
                  input={<OutlinedInput label="Select Resorts to Compare" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip
                          key={value}
                          label={value}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  )}
                  MenuProps={MenuProps}
                >
                  {Array.isArray(resorts) &&
                    resorts.map((resort) => (
                      <MenuItem key={resort} value={resort}>
                        <Checkbox
                          checked={selectedResorts.indexOf(resort) > -1}
                        />
                        <ListItemText primary={resort} />
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Time Range</InputLabel>
                <Select
                  value={timeRange}
                  label="Time Range"
                  onChange={(e) => setTimeRange(parseInt(e.target.value))}
                >
                  <MenuItem value={3}>Last 3 months</MenuItem>
                  <MenuItem value={6}>Last 6 months</MenuItem>
                  <MenuItem value={12}>Last 12 months</MenuItem>
                  <MenuItem value={24}>Last 24 months</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {loadingData && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Loading comparison data...
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {selectedResorts.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Please select at least one resort to compare.
        </Alert>
      )}

      {comparisonData.length > 0 && (
        <>
          {/* Recommendations */}
          <Box sx={{ mb: 3 }}>
            <ResortRecommendations />
          </Box>

          {/* Comparison Table */}
          <Box sx={{ mb: 3 }}>
            <ComparisonTable />
          </Box>

          {/* Charts */}
          <Grid container spacing={3}>
            <Grid item xs={12} lg={6}>
              <PriceComparisonChart />
            </Grid>
            <Grid item xs={12} lg={6}>
              <ResortScoreCard />
            </Grid>
          </Grid>

          {/* Insights */}
          <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Comparison Insights
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Typography
                  variant="subtitle2"
                  color="primary.main"
                  gutterBottom
                >
                  Price Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Compare average prices, ranges, and trends to identify the
                  best value propositions and understand market positioning.
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography
                  variant="subtitle2"
                  color="primary.main"
                  gutterBottom
                >
                  ROFR Risk Assessment
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Lower ROFR rates indicate higher likelihood of successful
                  resale purchases. Consider this alongside pricing for risk
                  evaluation.
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography
                  variant="subtitle2"
                  color="primary.main"
                  gutterBottom
                >
                  Market Activity
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Higher activity levels suggest better liquidity for both
                  buying and selling, providing more opportunities and price
                  discovery.
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default ResortComparison;
