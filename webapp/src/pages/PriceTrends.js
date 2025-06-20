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
  TextField,
  Button,
  Chip,
  Paper,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Slider,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ShowChartIcon,
  Timeline as TimelineIcon,
  Analytics as AnalyticsIcon,
} from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useTheme } from "@mui/material/styles";
import { useApi } from "../context/ApiContext";
import PriceTrendChart from "../components/charts/PriceTrendChart";

const PriceTrends = () => {
  const theme = useTheme();
  const { getPriceTrendsAnalysis, getResorts, loading, error, prefetchData } =
    useApi();

  const [data, setData] = useState(null);
  const [resorts, setResorts] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [selectedResort, setSelectedResort] = useState("BWV");
  const [timeRange, setTimeRange] = useState(12);
  const [chartType, setChartType] = useState("combined");
  const [priceRange, setPriceRange] = useState([0, 300]);
  const [customStartDate, setCustomStartDate] = useState(null);
  const [customEndDate, setCustomEndDate] = useState(null);

  // Fetch data using the new dedicated API endpoint
  const fetchPriceTrendsData = useCallback(
    async (filters = {}) => {
      try {
        const response = await getPriceTrendsAnalysis(filters);

        return response?.data || response;
      } catch (err) {
        console.error("Error fetching price trends data:", err);
        throw err;
      }
    },
    [getPriceTrendsAnalysis],
  );

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoadingData(true);
      try {
        // Prefetch resorts data for better performance
        await prefetchData(["resorts"]);

        const resortsData = await getResorts();
        console.log("Resorts data received:", resortsData);
        setResorts(resortsData.data || []);
        console.log("Resorts state set to:", resortsData.data || []);

        // Fetch initial data using the new endpoint
        // Wait a bit to ensure resorts are loaded if selectedResort is set
        if (
          selectedResort &&
          resortsData.data &&
          !resortsData.data.includes(selectedResort)
        ) {
          console.warn(
            "Selected resort",
            selectedResort,
            "not found in available resorts:",
            resortsData.data,
          );
        }

        const filters = {
          resort: selectedResort || undefined,
          timeRange: timeRange,
          minPrice: priceRange[0],
          maxPrice: priceRange[1],
        };

        console.log("Initial data fetch with filters:", filters);
        const trendsData = await fetchPriceTrendsData(filters);
        console.log("Initial trends data received:", trendsData);
        setData(trendsData);
        console.log("Data state set to:", trendsData);
      } catch (err) {
        console.error("Error fetching price trends:", err);
      } finally {
        setLoadingData(false);
      }
    };

    fetchInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getResorts, timeRange, priceRange, prefetchData, fetchPriceTrendsData]);

  const handleResortChange = async (resort) => {
    console.log("Resort change triggered:", resort);
    setSelectedResort(resort);
    setLoadingData(true);
    try {
      const filters = {
        resort: resort || undefined,
        timeRange: timeRange,
        minPrice: priceRange[0],
        maxPrice: priceRange[1],
      };

      console.log("Fetching data with filters:", filters);
      const trendsData = await fetchPriceTrendsData(filters);
      console.log("Received trends data:", trendsData);
      setData(trendsData);
      console.log("Data state updated to:", trendsData);
    } catch (err) {
      console.error("Error fetching resort trends:", err);
    } finally {
      setLoadingData(false);
    }
  };

  const handleTimeRangeChange = async (months) => {
    setTimeRange(months);
    setLoadingData(true);
    try {
      const filters = {
        resort: selectedResort || undefined,
        timeRange: months,
        minPrice: priceRange[0],
        maxPrice: priceRange[1],
      };

      const trendsData = await fetchPriceTrendsData(filters);
      setData(trendsData);
    } catch (err) {
      console.error("Error fetching time range trends:", err);
    } finally {
      setLoadingData(false);
    }
  };

  const handlePriceRangeChange = async (newPriceRange) => {
    setPriceRange(newPriceRange);
    setLoadingData(true);
    try {
      const filters = {
        resort: selectedResort || undefined,
        timeRange: timeRange,
        minPrice: newPriceRange[0],
        maxPrice: newPriceRange[1],
      };

      const trendsData = await fetchPriceTrendsData(filters);
      setData(trendsData);
    } catch (err) {
      console.error("Error fetching price range trends:", err);
    } finally {
      setLoadingData(false);
    }
  };

  const calculateTrendDirection = (trends) => {
    if (!trends || !Array.isArray(trends) || trends.length < 2) return null;

    const recent = trends.slice(-3); // Last 3 months
    const avgRecent =
      recent.reduce((sum, t) => sum + t.averagePrice, 0) / recent.length;

    const earlier = trends.slice(-6, -3); // 3-6 months ago
    const avgEarlier =
      earlier.length > 0
        ? earlier.reduce((sum, t) => sum + t.averagePrice, 0) / earlier.length
        : avgRecent;

    const change = ((avgRecent - avgEarlier) / avgEarlier) * 100;

    return {
      direction: change > 2 ? "up" : change < -2 ? "down" : "stable",
      percentage: Math.abs(change),
      value: change,
    };
  };

  const MarketInsightsCard = ({ trends, summary }) => {
    if (!trends || !summary) return null;

    const trend = calculateTrendDirection(trends);

    const latestMonth = trends[trends.length - 1];
    const previousMonth = trends[trends.length - 2];

    const monthlyChange =
      latestMonth && previousMonth
        ? ((latestMonth.averagePrice - previousMonth.averagePrice) /
            previousMonth.averagePrice) *
          100
        : 0;

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {summary.filters?.resort
              ? `${summary.filters.resort} Market Insights`
              : "Market Insights"}
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Box
                sx={{
                  textAlign: "center",
                  p: 2,
                  backgroundColor: "primary.light",
                  borderRadius: 1,
                }}
              >
                <Typography variant="h4" color="primary.contrastText">
                  ${summary.averagePrice?.toFixed(2) || "0"}
                </Typography>
                <Typography variant="body2" color="primary.contrastText">
                  {summary.filters?.resort
                    ? `${summary.filters.resort} Avg Price`
                    : "Current Avg Price"}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Box
                sx={{
                  textAlign: "center",
                  p: 2,
                  backgroundColor:
                    monthlyChange >= 0 ? "success.light" : "error.light",
                  borderRadius: 1,
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    mb: 1,
                  }}
                >
                  {monthlyChange >= 0 ? (
                    <TrendingUpIcon color="inherit" />
                  ) : (
                    <TrendingDownIcon color="inherit" />
                  )}
                  <Typography variant="h4" color="inherit" sx={{ ml: 1 }}>
                    {monthlyChange.toFixed(1)}%
                  </Typography>
                </Box>
                <Typography variant="body2" color="inherit">
                  Monthly Change
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Box
                sx={{
                  textAlign: "center",
                  p: 2,
                  backgroundColor: "warning.light",
                  borderRadius: 1,
                }}
              >
                <Typography variant="h4" color="warning.contrastText">
                  {summary.overallROFRRate?.toFixed(1) || "0"}%
                </Typography>
                <Typography variant="body2" color="warning.contrastText">
                  {summary.filters?.resort
                    ? `${summary.filters.resort} ROFR Rate`
                    : "ROFR Rate"}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Box
                sx={{
                  textAlign: "center",
                  p: 2,
                  backgroundColor: "secondary.light",
                  borderRadius: 1,
                }}
              >
                <Typography variant="h4" color="secondary.contrastText">
                  {summary.totalEntries || 0}
                </Typography>
                <Typography variant="body2" color="secondary.contrastText">
                  Total Contracts
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {trend && (
            <Box
              sx={{
                mt: 3,
                p: 2,
                backgroundColor: "background.default",
                borderRadius: 1,
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                3-Month Trend Analysis{" "}
                {summary.filters?.resort
                  ? `(${summary.filters.resort})`
                  : "(All Resorts)"}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {trend.direction === "up" && <TrendingUpIcon color="success" />}
                {trend.direction === "down" && (
                  <TrendingDownIcon color="error" />
                )}
                {trend.direction === "stable" && <TimelineIcon color="info" />}

                <Typography variant="body2">
                  Prices are{" "}
                  <strong>
                    {trend.direction === "up"
                      ? "trending up"
                      : trend.direction === "down"
                        ? "trending down"
                        : "stable"}
                  </strong>
                  {trend.direction !== "stable" && (
                    <span>
                      {" "}
                      by {trend.percentage.toFixed(1)}% over the last 3 months
                    </span>
                  )}
                </Typography>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  const PriceDistributionCard = ({ trends }) => {
    if (!trends || !Array.isArray(trends) || trends.length === 0) return null;

    // Calculate price distribution from individual prices
    const allPrices = trends.flatMap((month) =>
      month.prices && Array.isArray(month.prices) ? month.prices : [],
    );

    const priceRanges = {
      "Under $75": allPrices.filter((p) => p < 75).length,
      "$75-$100": allPrices.filter((p) => p >= 75 && p < 100).length,
      "$100-$125": allPrices.filter((p) => p >= 100 && p < 125).length,
      "$125-$150": allPrices.filter((p) => p >= 125 && p < 150).length,
      "$150-$200": allPrices.filter((p) => p >= 150 && p < 200).length,
      "Over $200": allPrices.filter((p) => p >= 200).length,
    };

    const maxCount = Math.max(...Object.values(priceRanges));

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Price Distribution
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {Object.entries(priceRanges).map(([range, count]) => (
              <Box
                key={range}
                sx={{ display: "flex", alignItems: "center", gap: 2 }}
              >
                <Typography variant="body2" sx={{ minWidth: 80 }}>
                  {range}
                </Typography>
                <Box sx={{ flexGrow: 1, position: "relative" }}>
                  <Box
                    sx={{
                      height: 8,
                      backgroundColor: "primary.main",
                      borderRadius: 4,
                      width: `${maxCount > 0 ? (count / maxCount) * 100 : 0}%`,
                    }}
                  />
                </Box>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ minWidth: 40 }}
                >
                  {count}
                </Typography>
              </Box>
            ))}
          </Box>
        </CardContent>
      </Card>
    );
  };

  const ROFRPredictionCard = ({ trends }) => {
    if (!trends || !Array.isArray(trends) || trends.length === 0) return null;

    // Calculate ROFR probability based on price
    const calculateROFRProbability = (pricePerPoint) => {
      // Simple heuristic based on historical data patterns
      const recentTrends = trends.slice(-6);
      const avgPrice =
        recentTrends.reduce((sum, t) => sum + t.averagePrice, 0) /
        recentTrends.length;
      const avgROFRRate =
        recentTrends.reduce((sum, t) => sum + t.rofrRate, 0) /
        recentTrends.length;

      const priceRatio = pricePerPoint / avgPrice;

      // Higher probability for lower prices
      let probability = avgROFRRate;
      if (priceRatio < 0.7) probability = Math.min(90, avgROFRRate * 3);
      else if (priceRatio < 0.8) probability = Math.min(60, avgROFRRate * 2);
      else if (priceRatio < 0.9) probability = Math.min(40, avgROFRRate * 1.5);
      else if (priceRatio > 1.2) probability = Math.max(1, avgROFRRate * 0.3);

      return Math.round(probability);
    };

    const samplePrices = [50, 75, 100, 125, 150, 200];

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ROFR Probability Estimator
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            gutterBottom
            sx={{ mb: 2 }}
          >
            Estimated probability of ROFR based on price per point
          </Typography>

          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {samplePrices.map((price) => {
              const probability = calculateROFRProbability(price);
              const color =
                probability > 60
                  ? "error"
                  : probability > 30
                    ? "warning"
                    : "success";

              return (
                <Box
                  key={price}
                  sx={{ display: "flex", alignItems: "center", gap: 2 }}
                >
                  <Typography variant="body2" sx={{ minWidth: 60 }}>
                    ${price}/pt
                  </Typography>
                  <Box sx={{ flexGrow: 1, position: "relative" }}>
                    <Box
                      sx={{
                        height: 8,
                        backgroundColor: `${color}.main`,
                        borderRadius: 4,
                        width: `${probability}%`,
                      }}
                    />
                  </Box>
                  <Chip
                    label={`${probability}%`}
                    size="small"
                    color={color}
                    variant="outlined"
                    sx={{ minWidth: 60 }}
                  />
                </Box>
              );
            })}
          </Box>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mt: 2, display: "block" }}
          >
            * Estimates based on historical patterns. Actual ROFR decisions may
            vary.
          </Typography>
        </CardContent>
      </Card>
    );
  };

  if (loadingData) {
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
        Error loading price trends: {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        Price Trends Analysis
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Comprehensive analysis of DVC contract pricing trends over time
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Resort</InputLabel>
                <Select
                  value={selectedResort}
                  label="Resort"
                  onChange={(e) => {
                    const newResort = e.target.value;
                    console.log("Select onChange triggered:", newResort);
                    console.log("Current selectedResort:", selectedResort);
                    console.log("Available resorts:", resorts);
                    console.log(
                      "Resort change from",
                      selectedResort,
                      "to",
                      newResort,
                    );
                    handleResortChange(newResort);
                  }}
                >
                  <MenuItem value="">All Resorts</MenuItem>
                  {Array.isArray(resorts) &&
                    resorts.map((resort) => {
                      console.log("Rendering resort option:", resort);
                      return (
                        <MenuItem key={resort} value={resort}>
                          {resort}
                        </MenuItem>
                      );
                    })}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" gutterBottom>
                Time Range (Months)
              </Typography>
              <ToggleButtonGroup
                value={timeRange}
                exclusive
                onChange={(e, value) => value && handleTimeRangeChange(value)}
                size="small"
              >
                <ToggleButton value={6}>6M</ToggleButton>
                <ToggleButton value={12}>1Y</ToggleButton>
                <ToggleButton value={24}>2Y</ToggleButton>
                <ToggleButton value={36}>3Y</ToggleButton>
              </ToggleButtonGroup>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" gutterBottom>
                Chart Type
              </Typography>
              <ToggleButtonGroup
                value={chartType}
                exclusive
                onChange={(e, value) => value && setChartType(value)}
                size="small"
              >
                <ToggleButton value="combined">
                  <ShowChartIcon />
                </ToggleButton>
                <ToggleButton value="analysis">
                  <AnalyticsIcon />
                </ToggleButton>
              </ToggleButtonGroup>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" gutterBottom>
                Price Range Filter ($)
              </Typography>
              <Slider
                value={priceRange}
                onChange={(e, value) => handlePriceRangeChange(value)}
                valueLabelDisplay="auto"
                min={0}
                max={300}
                step={25}
                marks={[
                  { value: 0, label: "$0" },
                  { value: 150, label: "$150" },
                  { value: 300, label: "$300" },
                ]}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Market Insights */}
      <Box sx={{ mb: 3 }}>
        <MarketInsightsCard
          trends={Array.isArray(data?.trends) ? data.trends : []}
          summary={data?.summary}
        />
        {/* Debug Info */}
        {console.log("Rendering MarketInsightsCard with data:", data)}
      </Box>

      {/* Active Filters Status */}
      {(selectedResort || priceRange[0] > 0 || priceRange[1] < 300) && (
        <Box sx={{ mb: 2 }}>
          <Alert severity="info" sx={{ maxWidth: 800 }}>
            <Typography variant="body2">
              <strong>Active Filters:</strong>{" "}
              {selectedResort && (
                <span>
                  Resort: <strong>{selectedResort}</strong>{" "}
                </span>
              )}
              {(priceRange[0] > 0 || priceRange[1] < 300) && (
                <span>
                  Price Range:{" "}
                  <strong>
                    ${priceRange[0]} - ${priceRange[1]}
                  </strong>
                </span>
              )}{" "}
              Data is filtered based on your selections.
            </Typography>
          </Alert>
        </Box>
      )}

      {/* Main Chart */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          {data?.trends &&
          Array.isArray(data.trends) &&
          data.trends.length > 0 ? (
            <>
              {console.log(
                "Rendering charts with trends data:",
                data.trends,
                "for resort:",
                selectedResort,
              )}
              {chartType === "combined" && (
                <PriceTrendChart
                  data={data.trends}
                  title={`Price Trends - ${selectedResort || "All Resorts"}`}
                  height={500}
                  showROFRThreshold={true}
                />
              )}
              {chartType === "analysis" && (
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <PriceTrendChart
                      data={data.trends}
                      title="Price Analysis"
                      height={350}
                      showROFRThreshold={true}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Filter Summary
                        </Typography>
                        <Box sx={{ p: 2 }}>
                          <Typography variant="body2" color="text.secondary">
                            Applied Filters:
                          </Typography>
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            Resort:{" "}
                            <strong>{selectedResort || "All Resorts"}</strong>
                          </Typography>
                          <Typography variant="body2">
                            Time Range: <strong>{timeRange} months</strong>
                          </Typography>
                          <Typography variant="body2">
                            Price Range:{" "}
                            <strong>
                              ${priceRange[0]} - ${priceRange[1]}
                            </strong>
                          </Typography>
                          <Typography variant="body2" sx={{ mt: 2 }}>
                            Results: <strong>{data.trends.length}</strong>{" "}
                            months, <strong>{data.summary.totalEntries}</strong>{" "}
                            entries
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              )}
            </>
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Price Trends Chart
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: 300,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No price trends data available for the selected filters.
                    Debug: data={data ? "exists" : "null"}, trends=
                    {Array.isArray(data?.trends)
                      ? `array[${data.trends.length}]`
                      : typeof data?.trends}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Analysis Cards */}
      {/* Detailed Analysis Cards */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <PriceDistributionCard
            trends={Array.isArray(data?.trends) ? data.trends : []}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <ROFRPredictionCard
            trends={Array.isArray(data?.trends) ? data.trends : []}
          />
        </Grid>
      </Grid>

      {/* Additional Insights */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Key Insights
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary.main" gutterBottom>
              Optimal Pricing Strategy
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Based on current trends, contracts priced 10-15% below market
              average have the best balance of competitive pricing while
              minimizing ROFR risk.
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary.main" gutterBottom>
              Market Timing
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Historical data shows pricing volatility is typically higher
              during Q4 (October-December) due to annual dues and holiday
              considerations.
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary.main" gutterBottom>
              ROFR Patterns
            </Typography>
            <Typography variant="body2" color="text.secondary">
              DVC's ROFR activity correlates with direct sales promotions and
              inventory management needs at specific resorts.
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default PriceTrends;
