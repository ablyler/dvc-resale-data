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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tabs,
  Tab,
  Divider,
  TableSortLabel,
} from "@mui/material";
import {
  FilterList as FilterIcon,
  Download as DownloadIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useTheme } from "@mui/material/styles";
import { useApi } from "../context/ApiContext";
import ROFRRateChart from "../components/charts/ROFRRateChart";
import PriceTrendChart from "../components/charts/PriceTrendChart";
import UsernameSelect from "../components/form/UsernameSelect";

const ROFRAnalytics = () => {
  const {
    getROFRAnalytics,
    getResorts,
    getUsernames,
    getMonthlyStats,
    exportROFRData,
    loading,
    error,
    prefetchData,
  } = useApi();

  const [data, setData] = useState(null);
  const [trendsData, setTrendsData] = useState([]);
  const [resorts, setResorts] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [activeTab, setActiveTab] = useState(0);

  // Filters
  const [filters, setFilters] = useState({
    resort: "",
    result: "",
    startDate: null,
    username: "",
    limit: 1000,
  });

  const [appliedFilters, setAppliedFilters] = useState({});

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoadingData(true);
      try {
        // Prefetch usernames for better performance
        if (prefetchData) {
          await prefetchData(["resorts", "usernames"]);
        }

        const [analyticsData, resortsData, monthlyData] = await Promise.all([
          getROFRAnalytics({ limit: 1000 }),
          getResorts(),
          getMonthlyStats(12), // Get 12 months of trends
        ]);

        setData(analyticsData?.data || analyticsData);
        setTrendsData(monthlyData?.data || []);
        setResorts(resortsData.data || []);
        setAppliedFilters({});
      } catch (err) {
        console.error("Error fetching ROFR analytics:", err);
      } finally {
        setLoadingData(false);
      }
    };

    fetchInitialData();
  }, [
    getROFRAnalytics,
    getResorts,
    getUsernames,
    getMonthlyStats,
    prefetchData,
  ]);

  // Generate trends data from individual entries
  const generateTrendsFromEntries = (entries) => {
    if (!entries || entries.length === 0) return [];

    // Group entries by month
    const monthlyData = {};

    entries.forEach((entry) => {
      if (!entry.sent_date) return;

      const date = new Date(entry.sent_date);
      const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, "0")}`;

      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = {
          month: monthKey,
          total: 0,
          taken: 0,
          passed: 0,
          pending: 0,
          prices: [],
        };
      }

      monthlyData[monthKey].total++;
      monthlyData[monthKey][entry.result || "pending"]++;

      if (entry.price_per_point && entry.price_per_point > 0) {
        monthlyData[monthKey].prices.push(entry.price_per_point);
      }
    });

    // Convert to trend format
    return Object.values(monthlyData)
      .map((month) => ({
        month: month.month,
        total: month.total,
        taken: month.taken,
        passed: month.passed,
        pending: month.pending,
        rofrRate: month.total > 0 ? (month.taken / month.total) * 100 : 0,
        averagePrice:
          month.prices.length > 0
            ? month.prices.reduce((sum, price) => sum + price, 0) /
              month.prices.length
            : 0,
        minPrice: month.prices.length > 0 ? Math.min(...month.prices) : 0,
        maxPrice: month.prices.length > 0 ? Math.max(...month.prices) : 0,
        priceCount: month.prices.length,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  };

  const handleFilterChange = useCallback((field, value) => {
    setFilters((prev) => {
      const newFilters = {
        ...prev,
        [field]: value,
      };
      return newFilters;
    });
  }, []);

  // Create a stable callback for username change handler
  const handleUsernameChange = useCallback((value) => {
    setFilters((prev) => ({
      ...prev,
      username: value,
    }));
  }, []);

  const applyFilters = async () => {
    setLoadingData(true);
    try {
      const filterParams = {
        ...filters,
        startDate: filters.startDate
          ? filters.startDate.toISOString().split("T")[0]
          : null,
      };

      // Remove empty filters
      const cleanFilters = Object.entries(filterParams).reduce(
        (acc, [key, value]) => {
          if (value !== "" && value !== null && value !== undefined) {
            acc[key] = value;
          }
          return acc;
        },
        {},
      );

      const analyticsData = await getROFRAnalytics(cleanFilters);

      const data = analyticsData?.data || analyticsData;

      setData(data);

      // Generate trends from filtered entries if available
      if (data?.entries && data.entries.length > 0) {
        const generatedTrends = generateTrendsFromEntries(data.entries);
        setTrendsData(generatedTrends);
      } else {
        // Fallback to global monthly stats if no entries
        const monthlyData = await getMonthlyStats(12);
        setTrendsData(monthlyData?.data || []);
      }
      setAppliedFilters(cleanFilters);
    } catch (err) {
      console.error("Error applying filters:", err);
    } finally {
      setLoadingData(false);
    }
  };

  const clearFilters = () => {
    setFilters({
      resort: "",
      result: "",
      startDate: null,
      username: "",
      limit: 1000,
    });
  };

  const handleExport = async (format = "csv") => {
    try {
      const exportData = await exportROFRData({
        ...appliedFilters,
        format,
        limit: 10000,
      });

      if (format === "csv") {
        // Create and download CSV
        const blob = new Blob([exportData], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `rofr-analytics-${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Error exporting data:", err);
    }
  };

  const ROFRRiskAnalysis = ({ analytics }) => {
    if (!analytics) return null;

    const riskThresholds = {
      low: 90,
      medium: 70,
      high: 50,
    };

    const getRiskLevel = (pricePerPoint) => {
      const avgPrice = analytics.averagePricePerPoint || 0;
      const percentage = (pricePerPoint / avgPrice) * 100;

      if (percentage >= riskThresholds.low)
        return { level: "Low", color: "success" };
      if (percentage >= riskThresholds.medium)
        return { level: "Medium", color: "warning" };
      return { level: "High", color: "error" };
    };

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ROFR Risk Analysis
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Current Market Insights
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    textAlign: "center",
                    p: 2,
                    backgroundColor: "success.light",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="h4" color="success.contrastText">
                    {analytics.rofrRate?.toFixed(1) || 0}%
                  </Typography>
                  <Typography variant="body2" color="success.contrastText">
                    Overall ROFR Rate
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    textAlign: "center",
                    p: 2,
                    backgroundColor: "primary.light",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="h4" color="primary.contrastText">
                    ${analytics.averagePricePerPoint?.toFixed(2) || 0}
                  </Typography>
                  <Typography variant="body2" color="primary.contrastText">
                    Avg Price/Point
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    textAlign: "center",
                    p: 2,
                    backgroundColor: "secondary.light",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="h4" color="secondary.contrastText">
                    {analytics.totalEntries || 0}
                  </Typography>
                  <Typography variant="body2" color="secondary.contrastText">
                    Total Entries
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="body2" color="text.secondary" gutterBottom>
            Risk Assessment Guidelines
          </Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
            <Chip
              icon={<TrendingUpIcon />}
              label="Low Risk: >90% of market avg"
              color="success"
              size="small"
              variant="outlined"
            />
            <Chip
              icon={<WarningIcon />}
              label="Medium Risk: 70-90% of market avg"
              color="warning"
              size="small"
              variant="outlined"
            />
            <Chip
              icon={<WarningIcon />}
              label="High Risk: <70% of market avg"
              color="error"
              size="small"
              variant="outlined"
            />
          </Box>

          <Typography variant="caption" color="text.secondary">
            Risk levels are calculated based on price per point relative to
            market average. Lower prices relative to market average indicate
            higher likelihood of ROFR buyback.
          </Typography>
        </CardContent>
      </Card>
    );
  };

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );

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
        Error loading analytics: {error}
      </Alert>
    );
  }

  if (!data || !data.analytics) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          No analytics data available. The API may be unavailable or returning
          empty data.
        </Alert>
        <Typography variant="body2" color="text.secondary">
          Debug: data = {data ? "exists" : "null"}, analytics ={" "}
          {data?.analytics ? "exists" : "null"}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        ROFR Analytics
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Detailed analysis of DVC's resale data
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <FilterIcon color="primary" />
            <Typography variant="h6">Filters</Typography>
          </Box>

          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Resort</InputLabel>
                <Select
                  value={filters.resort}
                  onChange={(e) => handleFilterChange("resort", e.target.value)}
                  label="Resort"
                >
                  <MenuItem value="">All Resorts</MenuItem>
                  {Array.isArray(resorts) &&
                    resorts.map((resort) => (
                      <MenuItem key={resort} value={resort}>
                        {resort}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.result}
                  onChange={(e) => handleFilterChange("result", e.target.value)}
                  label="Status"
                >
                  <MenuItem value="">All Status</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                  <MenuItem value="passed">Passed</MenuItem>
                  <MenuItem value="taken">Taken</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="Start Date"
                  value={filters.startDate}
                  onChange={(date) => handleFilterChange("startDate", date)}
                  renderInput={(params) => (
                    <TextField {...params} size="small" fullWidth />
                  )}
                />
              </LocalizationProvider>
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <UsernameSelect
                key="stable-username-input"
                label="Username"
                value={filters.username}
                onChange={handleUsernameChange}
                size="small"
                fullWidth
                placeholder="Select username"
              />
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Limit"
                type="number"
                value={filters.limit}
                onChange={(e) =>
                  handleFilterChange("limit", parseInt(e.target.value))
                }
                size="small"
                fullWidth
                inputProps={{ min: 100, max: 5000, step: 100 }}
              />
            </Grid>

            <Grid item xs={12} sm={6} md={2}>
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={applyFilters}
                  disabled={loading}
                  size="small"
                >
                  Apply
                </Button>
                <Button variant="outlined" onClick={clearFilters} size="small">
                  Clear
                </Button>
              </Box>
            </Grid>
          </Grid>

          {/* Active Filters */}
          {Object.keys(appliedFilters).length > 0 && (
            <Box sx={{ mt: 2, display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Typography variant="body2" color="text.secondary">
                Active filters:
              </Typography>
              {Object.entries(appliedFilters).map(([key, value]) => (
                <Chip
                  key={key}
                  label={`${key}: ${value}`}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Export Actions */}
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => handleExport("csv")}
          disabled={loading}
        >
          Export CSV
        </Button>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
        >
          <Tab label="Overview" />
          <Tab label="Risk Analysis" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={activeTab} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            {trendsData &&
            Array.isArray(trendsData) &&
            trendsData.length > 0 ? (
              <PriceTrendChart
                data={trendsData}
                title="Price Trends Analysis"
                height={400}
                showROFRThreshold={true}
              />
            ) : (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Price Trends Analysis
                  </Typography>
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      No price trend data available.
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 1 }}
                    >
                      Debug: trendsData ={" "}
                      {Array.isArray(trendsData)
                        ? `array[${trendsData.length}]`
                        : typeof trendsData}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            )}
          </Grid>
          <Grid item xs={12} lg={6}>
            {trendsData &&
            Array.isArray(trendsData) &&
            trendsData.length > 0 ? (
              <ROFRRateChart
                data={trendsData}
                title="ROFR Rate Analysis"
                height={400}
              />
            ) : (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    ROFR Rate Analysis
                  </Typography>
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      No ROFR rate trend data available.
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 1 }}
                    >
                      Debug: trendsData ={" "}
                      {Array.isArray(trendsData)
                        ? `array[${trendsData.length}]`
                        : typeof trendsData}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            )}
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <ROFRRiskAnalysis analytics={data?.analytics} />
      </TabPanel>
    </Box>
  );
};

export default ROFRAnalytics;
