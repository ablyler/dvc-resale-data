import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  LinearProgress,
  Tooltip,
  IconButton,
  Container,
  FormControl,
  Select,
  MenuItem,
} from "@mui/material";
import { format, parseISO, isToday, differenceInDays } from "date-fns";
import {
  TrendingUp,
  TrendingDown,
  AttachMoney,
  Assessment,
  Refresh,
  Speed,
  Insights,
  Update,
  Schedule,
} from "@mui/icons-material";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useApi } from "../context/ApiContext";
import ROFRRateChart from "../components/charts/ROFRRateChart";
import PriceTrendChart from "../components/charts/PriceTrendChart";
import {
  testTimeRangeCaching,
  monitorCacheBehavior,
  validateCacheKeys,
} from "../utils/cacheTestUtils";

const Dashboard = () => {
  const {
    getDashboardData,
    prefetchData,
    clearCache,
    getCacheStats,
    isCached,
    prefetchTimeRange,
    error,
  } = useApi();
  const [dashboardData, setDashboardData] = useState(null);
  const [loadingData, setLoadingData] = useState(true);
  const [cacheStats, setCacheStats] = useState({ size: 0, keys: [] });
  const [timeRange, setTimeRange] = useState("3months");
  const [loadingFromCache, setLoadingFromCache] = useState(false);
  const [lastCacheHit, setLastCacheHit] = useState(null);
  const [prefetchingRanges, setPrefetchingRanges] = useState(new Set());
  const [showCacheDebug, setShowCacheDebug] = useState(false);

  const timeRangeOptions = useMemo(
    () => [
      { value: "3months", label: "Last 3 months" },
      { value: "6months", label: "Last 6 months" },
      { value: "1year", label: "Last year" },
    ],
    [],
  );

  // Parse date strings (like "2025-01-15") as simple dates without timezone conversion
  const parseSimpleDate = (dateString) => {
    if (!dateString) return null;
    // For ISO date strings (YYYY-MM-DD), parse directly without timezone handling
    return parseISO(dateString);
  };

  // Get relative time description for a date
  const getRelativeTimeLabel = (date) => {
    if (!date) return null;

    if (isToday(date)) {
      return "today";
    }

    const daysAgo = differenceInDays(new Date(), date);
    if (daysAgo === 1) {
      return "1 day ago";
    } else if (daysAgo > 1) {
      return `${daysAgo} days ago`;
    } else if (daysAgo === -1) {
      return "tomorrow";
    } else if (daysAgo < -1) {
      return `in ${Math.abs(daysAgo)} days`;
    }

    return "today";
  };

  // Prefetch commonly used data on component mount
  useEffect(() => {
    prefetchData(["resorts", "rofr-stats", "rofr-monthly-stats"]);

    // Prefetch other time ranges after initial load
    const prefetchOtherRanges = async () => {
      const otherRanges = timeRangeOptions
        .map((opt) => opt.value)
        .filter((range) => range !== timeRange);

      // Delay prefetching to not interfere with initial load
      setTimeout(async () => {
        for (const range of otherRanges) {
          if (!isCached("dashboard-data", { time_range: range })) {
            setPrefetchingRanges((prev) => new Set([...prev, range]));
            await prefetchTimeRange(range);
            setPrefetchingRanges((prev) => {
              const newSet = new Set(prev);
              newSet.delete(range);
              return newSet;
            });
          }
        }
      }, 2000); // Wait 2 seconds after initial load
    };

    prefetchOtherRanges();

    // Add cache monitoring in development
    if (process.env.NODE_ENV === "development") {
      const cleanup = monitorCacheBehavior({
        getDashboardData,
        isCached,
        clearCache,
      });
      return cleanup;
    }
  }, [
    prefetchData,
    timeRange,
    timeRangeOptions,
    isCached,
    prefetchTimeRange,
    getDashboardData,
    clearCache,
  ]);

  const fetchDashboardData = useCallback(
    async (forceRefresh = false, selectedTimeRange = null) => {
      const rangeToUse = selectedTimeRange || timeRange;

      // Check if data is cached using the new isCached method
      const dataIsCached = isCached("dashboard-data", {
        time_range: rangeToUse,
      });

      if (dataIsCached && !forceRefresh) {
        setLoadingFromCache(true);
        setLastCacheHit(rangeToUse);
      } else {
        setLoadingData(true);
        setLastCacheHit(null);
      }

      try {
        if (forceRefresh) {
          // Clear relevant cache before fetching
          clearCache("dashboard");
          clearCache("rofr-stats");
          clearCache("rofr-monthly-stats");
          clearCache("rofr-analytics");
          clearCache("price-trends");
        }

        // Use consolidated dashboard endpoint with time range
        const response = await getDashboardData(rangeToUse);
        setDashboardData(response?.data || response);
        setCacheStats(getCacheStats());

        // Set cache hit info if this was a cached response
        if (dataIsCached && !forceRefresh) {
          setLastCacheHit(rangeToUse);
        }
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
      } finally {
        setLoadingData(false);
        setLoadingFromCache(false);
      }
    },
    [getDashboardData, clearCache, getCacheStats, isCached, timeRange],
  );

  useEffect(() => {
    fetchDashboardData();
    // Update cache stats
    setCacheStats(getCacheStats());
  }, [fetchDashboardData, getCacheStats]);

  // Fetch data when time range changes
  useEffect(() => {
    if (timeRange) {
      fetchDashboardData(false, timeRange);
    }
  }, [timeRange, fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData(true);
  };

  const handleTimeRangeChange = (event) => {
    const newTimeRange = event.target.value;
    setTimeRange(newTimeRange);

    // Clear the last cache hit to show fresh loading state
    setLastCacheHit(null);

    // If switching to a range that's not cached, prefetch others
    if (!isCached("dashboard-data", { time_range: newTimeRange })) {
      // Prefetch other ranges after this one loads
      setTimeout(() => {
        const otherRanges = timeRangeOptions
          .map((opt) => opt.value)
          .filter(
            (range) =>
              range !== newTimeRange &&
              !isCached("dashboard-data", { time_range: range }),
          );

        otherRanges.forEach(async (range) => {
          setPrefetchingRanges((prev) => new Set([...prev, range]));
          await prefetchTimeRange(range);
          setPrefetchingRanges((prev) => {
            const newSet = new Set(prev);
            newSet.delete(range);
            return newSet;
          });
        });
      }, 1000);
    }
  };

  const getTimeRangeLabel = () => {
    const option = timeRangeOptions.find((opt) => opt.value === timeRange);
    return option ? option.label : "Last 3 months";
  };

  // Cache testing functions for debugging
  const runCacheTest = async () => {
    console.log("🧪 Running cache test...");
    const results = await testTimeRangeCaching(
      { getDashboardData, isCached, clearCache },
      timeRangeOptions.map((opt) => opt.value),
    );
    console.log("Test results:", results);
  };

  const validateCache = () => {
    console.log("🔍 Validating cache...");
    const validation = validateCacheKeys(getCacheStats());
    console.log("Validation results:", validation);
  };

  const MetricCard = ({
    title,
    value,
    subtitle,
    icon,
    color = "primary",
    trend = null,
    isLoading = false,
  }) => (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 1,
              backgroundColor: `${color}.light`,
              color: `${color}.contrastText`,
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
          {trend && (
            <Chip
              icon={trend > 0 ? <TrendingUp /> : <TrendingDown />}
              label={`${trend > 0 ? "+" : ""}${trend.toFixed(1)}%`}
              color={trend > 0 ? "success" : "error"}
              size="small"
            />
          )}
        </Box>

        {isLoading ? (
          <Box
            sx={{ display: "flex", alignItems: "center", minHeight: "60px" }}
          >
            <CircularProgress size={24} sx={{ mr: 2 }} />
            <Typography variant="body2" color="text.secondary">
              Loading...
            </Typography>
          </Box>
        ) : (
          <>
            <Typography variant="h4" component="div" color={`${color}.main`}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );

  const CacheStatusCard = () => {
    const timeRangeCacheKeys = cacheStats.keys.filter((key) =>
      key.startsWith("dashboard-data:"),
    );

    const getCachedTimeRanges = () => {
      return timeRangeCacheKeys
        .map((key) => {
          const match = key.match(/time_range":"([^"]+)"/);
          return match ? match[1] : null;
        })
        .filter(Boolean);
    };

    const cachedRanges = getCachedTimeRanges();

    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Speed sx={{ mr: 1, color: "primary.main" }} />
              <Typography variant="subtitle2">
                Cache Status: {cacheStats.size} items cached
              </Typography>
            </Box>
            {cachedRanges.length > 0 && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Time ranges cached:
                </Typography>
                {cachedRanges.map((range) => (
                  <Chip
                    key={range}
                    label={range}
                    size="small"
                    variant={range === timeRange ? "filled" : "outlined"}
                    color={range === timeRange ? "primary" : "default"}
                    sx={{ fontSize: "0.7rem" }}
                  />
                ))}
                {Array.from(prefetchingRanges).map((range) => (
                  <Chip
                    key={`prefetch-${range}`}
                    label={`${range} (prefetching...)`}
                    size="small"
                    variant="outlined"
                    color="info"
                    sx={{ fontSize: "0.7rem" }}
                  />
                ))}
              </Box>
            )}
            {lastCacheHit && (
              <Chip
                label={`Cache hit: ${lastCacheHit}`}
                size="small"
                color="success"
                variant="outlined"
                sx={{ fontSize: "0.7rem" }}
              />
            )}
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {process.env.NODE_ENV === "development" && (
              <>
                <Tooltip title="Toggle cache debug info">
                  <IconButton
                    onClick={() => setShowCacheDebug(!showCacheDebug)}
                    size="small"
                    color={showCacheDebug ? "primary" : "default"}
                  >
                    <Assessment />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Run cache test">
                  <IconButton
                    onClick={runCacheTest}
                    size="small"
                    disabled={loadingData || loadingFromCache}
                  >
                    <Speed />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Validate cache">
                  <IconButton onClick={validateCache} size="small">
                    <Insights />
                  </IconButton>
                </Tooltip>
              </>
            )}
            <Tooltip title="Refresh all data">
              <IconButton
                onClick={handleRefresh}
                disabled={loadingData || loadingFromCache}
              >
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        {showCacheDebug && process.env.NODE_ENV === "development" && (
          <Box sx={{ mt: 2, p: 2, bgcolor: "grey.100", borderRadius: 1 }}>
            <Typography
              variant="caption"
              sx={{ fontFamily: "monospace", display: "block", mb: 1 }}
            >
              Cache Debug Info:
            </Typography>
            <Typography
              variant="caption"
              sx={{ fontFamily: "monospace", display: "block" }}
            >
              {JSON.stringify(cacheStats, null, 2)}
            </Typography>
          </Box>
        )}
      </Paper>
    );
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading dashboard: {error}
        </Alert>
        <Typography variant="body2" color="text.secondary">
          Please try refreshing the page or contact support if the issue
          persists.
        </Typography>
      </Box>
    );
  }

  const displayStats = dashboardData?.global_stats;
  const displayTrends = Array.isArray(dashboardData?.monthly_stats)
    ? dashboardData.monthly_stats
    : [];
  const lastScrapedEntry = dashboardData?.global_stats?.last_updated;

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          mb: 3,
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, flexGrow: 1 }}
        >
          <Insights color="primary" sx={{ fontSize: 32 }} />
          <Typography variant="h4" component="h1">
            DVC Resale Data
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <Select
              value={timeRange}
              onChange={handleTimeRangeChange}
              displayEmpty
              disabled={loadingData || loadingFromCache}
              sx={{
                bgcolor: "background.paper",
                "& .MuiOutlinedInput-notchedOutline": {
                  borderColor: "divider",
                },
              }}
            >
              {timeRangeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {loadingData && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <LinearProgress sx={{ width: 200, borderRadius: 1 }} />
              <Typography variant="caption" color="text.secondary">
                Loading...
              </Typography>
            </Box>
          )}
          {loadingFromCache && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <LinearProgress
                sx={{ width: 200, borderRadius: 1 }}
                color="success"
                variant="indeterminate"
              />
              <Typography variant="caption" color="success.main">
                Loading from cache...
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      <CacheStatusCard />

      {/* Data Filtering Info */}
      <Paper sx={{ p: 2, mb: 2, bgcolor: "info.50" }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={getTimeRangeLabel()}
              color="info"
              size="small"
              variant="outlined"
            />
            <Typography variant="body2" color="text.secondary">
              Showing {displayStats?.total_entries?.toLocaleString() || "0"}{" "}
              entries
              {dashboardData?.total_entries_available &&
                dashboardData.total_entries_available !==
                  displayStats?.total_entries && (
                  <span>
                    {" "}
                    (filtered from{" "}
                    {dashboardData.total_entries_available.toLocaleString()}{" "}
                    total)
                  </span>
                )}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Last Scraped Entry Info */}
      <Paper
        sx={{
          p: 2,
          mb: 2,
          bgcolor: lastScrapedEntry ? "success.50" : "grey.50",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Box
              sx={{
                p: 1,
                borderRadius: 1,
                backgroundColor: lastScrapedEntry ? "success.main" : "grey.400",
                color: lastScrapedEntry ? "success.contrastText" : "grey.50",
                mr: 2,
              }}
            >
              <Update />
            </Box>
            <Box>
              <Typography
                variant="subtitle2"
                color="text.primary"
                fontWeight="medium"
              >
                Lastest Contract ROFR Sent Date
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {lastScrapedEntry
                  ? format(parseSimpleDate(lastScrapedEntry), "MMM d, yyyy")
                  : "No data available"}
              </Typography>
            </Box>
          </Box>
          {lastScrapedEntry && (
            <Tooltip
              title={`Date when most recent ROFR was sent: ${lastScrapedEntry}`}
            >
              <Chip
                label={
                  getRelativeTimeLabel(parseSimpleDate(lastScrapedEntry)) ||
                  "unknown"
                }
                size="small"
                color="success"
                variant="outlined"
              />
            </Tooltip>
          )}
        </Box>
      </Paper>

      <Grid container spacing={{ xs: 2, md: 3 }}>
        {/* Key Metrics Row */}
        <Grid item xs={12} sm={6} lg={3}>
          <MetricCard
            title="Total Entries"
            value={displayStats?.total_entries?.toLocaleString() || "0"}
            subtitle={`ROFR records (${getTimeRangeLabel()})`}
            icon={<Assessment />}
            color="primary"
            isLoading={loadingData}
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <MetricCard
            title="ROFR Rate"
            value={
              displayStats?.rofr_rate
                ? `${displayStats.rofr_rate.toFixed(1)}%`
                : "0%"
            }
            subtitle={`Taken vs Total (${getTimeRangeLabel()})`}
            icon={<TrendingUp />}
            color="error"
            isLoading={loadingData}
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <MetricCard
            title="Avg Price/Point"
            value={
              displayStats?.avg_price_per_point
                ? `$${displayStats.avg_price_per_point.toFixed(0)}`
                : "$0"
            }
            subtitle={`Market average (${getTimeRangeLabel()})`}
            icon={<AttachMoney />}
            color="warning"
            isLoading={loadingData}
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <MetricCard
            title="Avg Days to Result"
            value={
              displayStats?.avg_days_to_result !== null &&
              displayStats?.avg_days_to_result !== undefined
                ? `${displayStats.avg_days_to_result} days`
                : "N/A"
            }
            subtitle={
              displayStats?.days_to_result_count > 0
                ? `Based on ${displayStats.days_to_result_count} entries (${getTimeRangeLabel()})`
                : "No completed entries"
            }
            icon={<Schedule />}
            color="info"
            isLoading={loadingData}
          />
        </Grid>

        {/* Charts Section */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ height: { xs: "350px", md: "400px" } }}>
            <CardContent
              sx={{ height: "100%", display: "flex", flexDirection: "column" }}
            >
              <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                ROFR Rate Trend ({getTimeRangeLabel()})
              </Typography>
              {loadingData ? (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexGrow: 1,
                  }}
                >
                  <CircularProgress />
                </Box>
              ) : displayTrends &&
                Array.isArray(displayTrends) &&
                displayTrends.length > 0 ? (
                <Box sx={{ flexGrow: 1, minHeight: 0 }}>
                  <ROFRRateChart data={displayTrends} />
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexGrow: 1,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No trend data available
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Card sx={{ height: { xs: "350px", md: "400px" } }}>
            <CardContent
              sx={{ height: "100%", display: "flex", flexDirection: "column" }}
            >
              <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                Price Trends ({getTimeRangeLabel()})
              </Typography>
              {loadingData ? (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexGrow: 1,
                  }}
                >
                  <CircularProgress />
                </Box>
              ) : displayTrends &&
                Array.isArray(displayTrends) &&
                displayTrends.length > 0 ? (
                <Box sx={{ flexGrow: 1, minHeight: 0 }}>
                  <PriceTrendChart data={displayTrends} />
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    flexGrow: 1,
                    gap: 1,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No price trend data available
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textAlign: "center", maxWidth: 300 }}
                  >
                    Debug: dashboardData={dashboardData ? "loaded" : "null"},
                    displayTrends=
                    {Array.isArray(displayTrends)
                      ? `array[${displayTrends.length}]`
                      : typeof displayTrends}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Data Summary Section */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                Top Resorts by Activity
              </Typography>
              {loadingData ? (
                <Box sx={{ p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : (
                <Box>
                  {displayStats?.resort_counts &&
                  Object.keys(displayStats.resort_counts).length > 0 ? (
                    Object.entries(displayStats.resort_counts)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([resort, count], index) => (
                        <Box
                          key={resort}
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            py: 1.5,
                            borderBottom: index < 4 ? "1px solid" : "none",
                            borderColor: "divider",
                          }}
                        >
                          <Typography variant="body1" fontWeight={500}>
                            {resort}
                          </Typography>
                          <Chip
                            label={`${count.toLocaleString()} entries`}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </Box>
                      ))
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No resort data available
                    </Typography>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                ROFR Results Summary
              </Typography>
              {loadingData ? (
                <Box sx={{ p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: "center", p: 1 }}>
                      <Typography
                        variant="h4"
                        color="error.main"
                        fontWeight="bold"
                      >
                        {(displayStats?.taken_count || 0).toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Taken by DVC
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: "center", p: 1 }}>
                      <Typography
                        variant="h4"
                        color="success.main"
                        fontWeight="bold"
                      >
                        {(displayStats?.passed_count || 0).toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Passed to Sale
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: "center", p: 1 }}>
                      <Typography
                        variant="h4"
                        color="warning.main"
                        fontWeight="bold"
                      >
                        {(displayStats?.pending_count || 0).toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Pending Decision
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: "center", p: 1 }}>
                      <Typography variant="h6" color="info.main">
                        {displayStats?.last_updated
                          ? format(
                              parseSimpleDate(displayStats.last_updated),
                              "MMM d, yyyy",
                            )
                          : "N/A"}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Last Updated
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Info */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, bgcolor: "grey.50", borderRadius: 2 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                Performance: Dashboard loaded with {cacheStats.size} cached
                items.
                {loadingData
                  ? " Data loading..."
                  : " All data loaded from optimized API endpoints."}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {displayStats?.is_fresh !== undefined
                  ? `Statistics: ${displayStats.is_fresh ? "Fresh" : "Cached"}`
                  : ""}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;
