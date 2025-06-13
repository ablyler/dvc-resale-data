import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from "react";
import axios from "axios";

const ApiContext = createContext();

// Default API base URL - can be overridden via environment variable
const DEFAULT_API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  "https://your-function-app.azurewebsites.net/api";

// Cache configuration
const CACHE_TTL = {
  resorts: 30 * 60 * 1000, // 30 minutes - rarely changes
  stats: 5 * 60 * 1000, // 5 minutes - updates periodically
  data: 2 * 60 * 1000, // 2 minutes - frequently changing
};

export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error("useApi must be used within an ApiProvider");
  }
  return context;
};

export const ApiProvider = ({ children }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiBaseUrl] = useState(DEFAULT_API_BASE_URL);

  // Cache and request management
  const cache = useRef(new Map());
  const pendingRequests = useRef(new Map());
  const batchTimeouts = useRef(new Map());

  // Create axios instance with default config
  const apiClient = axios.create({
    baseURL: apiBaseUrl,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Cache helpers
  const getCacheKey = (endpoint, params = {}) => {
    const sortedParams = Object.keys(params)
      .sort()
      .reduce((result, key) => {
        result[key] = params[key];
        return result;
      }, {});
    return `${endpoint}:${JSON.stringify(sortedParams)}`;
  };

  const setCache = (key, data, ttl) => {
    cache.current.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  };

  const getCache = (key) => {
    const entry = cache.current.get(key);
    if (entry && Date.now() - entry.timestamp < entry.ttl) {
      return entry.data;
    }
    // Remove expired cache
    if (entry) {
      cache.current.delete(key);
    }
    return null;
  };

  // Clear expired cache entries periodically
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      for (const [key, entry] of cache.current.entries()) {
        if (now - entry.timestamp > entry.ttl) {
          cache.current.delete(key);
        }
      }
    }, 60000); // Clean every minute

    return () => clearInterval(interval);
  }, []);

  // Generic API call handler with caching and deduplication
  const apiCall = useCallback(
    async (endpoint, options = {}, cacheTTL = 0) => {
      const cacheKey = getCacheKey(endpoint, options.params);

      // Check cache first
      if (cacheTTL > 0) {
        const cachedData = getCache(cacheKey);
        if (cachedData) {
          return cachedData;
        }
      }

      // Check if request is already pending (deduplication)
      if (pendingRequests.current.has(cacheKey)) {
        return pendingRequests.current.get(cacheKey);
      }

      const requestPromise = (async () => {
        setLoading(true);
        setError(null);

        try {
          const response = await apiClient({
            url: endpoint,
            method: "GET",
            ...options,
          });

          if (response.data && response.data.status === "error") {
            throw new Error(response.data.error || "API request failed");
          }

          // Cache successful responses
          if (cacheTTL > 0) {
            setCache(cacheKey, response.data, cacheTTL);
          }

          return response.data;
        } catch (err) {
          const errorMessage =
            err.response?.data?.error ||
            err.message ||
            "An unexpected error occurred";
          setError(errorMessage);
          throw new Error(errorMessage);
        } finally {
          setLoading(false);
          pendingRequests.current.delete(cacheKey);
        }
      })();

      pendingRequests.current.set(cacheKey, requestPromise);
      return requestPromise;
    },
    [apiClient],
  );

  // Batch API calls to reduce network requests
  const batchApiCall = useCallback(
    async (calls, batchKey = "default", delay = 50) => {
      return new Promise((resolve) => {
        // Clear existing timeout for this batch
        if (batchTimeouts.current.has(batchKey)) {
          clearTimeout(batchTimeouts.current.get(batchKey));
        }

        // Set timeout to execute batch
        const timeout = setTimeout(async () => {
          try {
            const results = await Promise.all(calls);
            resolve(results);
          } catch (error) {
            resolve(calls.map(() => ({ error: error.message })));
          } finally {
            batchTimeouts.current.delete(batchKey);
          }
        }, delay);

        batchTimeouts.current.set(batchKey, timeout);
      });
    },
    [],
  );

  // Core API methods with caching
  const getResorts = useCallback(async () => {
    return await apiCall("resorts", {}, CACHE_TTL.resorts);
  }, [apiCall]);

  const getUsernames = useCallback(async () => {
    return await apiCall("usernames", {}, CACHE_TTL.resorts);
  }, [apiCall]);

  const getROFRStats = useCallback(async () => {
    return await apiCall("rofr-stats", {}, CACHE_TTL.stats);
  }, [apiCall]);

  const getMonthlyStats = useCallback(
    async (months = 12) => {
      const params = new URLSearchParams();
      params.append("months", months.toString());
      const endpoint = `rofr-monthly-stats?${params.toString()}`;
      return await apiCall(endpoint, {}, CACHE_TTL.stats);
    },
    [apiCall],
  );

  const getROFRData = useCallback(
    async (filters = {}) => {
      const params = new URLSearchParams();

      if (filters.resort) params.append("resort", filters.resort);
      if (filters.result) params.append("result", filters.result);
      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.endDate) params.append("end_date", filters.endDate);
      if (filters.username) params.append("username", filters.username);
      if (filters.use_year) params.append("use_year", filters.use_year);
      if (filters.min_price) params.append("min_price", filters.min_price);
      if (filters.max_price) params.append("max_price", filters.max_price);
      if (filters.min_points) params.append("min_points", filters.min_points);
      if (filters.max_points) params.append("max_points", filters.max_points);
      if (filters.min_total_cost)
        params.append("min_total_cost", filters.min_total_cost);
      if (filters.exclude_result)
        params.append("exclude_result", filters.exclude_result);
      if (filters.limit)
        params.append(
          "limit",
          Math.min(filters.limit || 1000, 1000).toString(),
        );
      if (filters.offset) params.append("offset", filters.offset.toString());
      if (filters.sort_by) params.append("sort_by", filters.sort_by);
      if (filters.sort_order) params.append("sort_order", filters.sort_order);

      const queryString = params.toString();
      const endpoint = `rofr-data${queryString ? `?${queryString}` : ""}`;

      try {
        // Use shorter cache for data that changes frequently
        const response = await apiCall(endpoint, {}, CACHE_TTL.data);

        // Handle API response format - data is directly in response.data array
        if (response && response.data && Array.isArray(response.data)) {
          const processedResponse = {
            ...response,
            entries: response.data, // Move data array to entries for compatibility
            count: response.data.length,
            meta: {
              count: response.data.length,
              total: response.data.length,
            },
          };
          return processedResponse;
        }

        // Handle legacy response format with entries array
        if (response && response.data && response.data.entries) {
          const processedResponse = {
            ...response,
            data: response.data.entries,
            meta: {
              count: response.data.count,
              limit_applied: response.data.limit_applied,
              has_more: response.data.has_more,
            },
          };
          return processedResponse;
        }

        return response;
      } catch (error) {
        console.error("ApiContext: Error in getROFRData:", error);
        throw error;
      }
    },
    [apiCall],
  );

  // Consolidated dashboard data - single API call to dashboard endpoint
  const getDashboardData = useCallback(
    async (timeRange = "3months") => {
      const params = { time_range: timeRange };
      const cacheKey = getCacheKey("dashboard-data", params);

      // Check if we're serving from cache for debugging
      const cachedData = getCache(cacheKey);
      if (cachedData) {
        console.log(`🎯 Cache hit for dashboard data (${timeRange})`);
      } else {
        console.log(`🔄 Fetching fresh dashboard data (${timeRange})`);
      }

      return await apiCall("dashboard-data", { params }, CACHE_TTL.stats);
    },
    [apiCall],
  );

  // Optimized analytics that can use server-side calculations
  const getROFRAnalytics = useCallback(
    async (filters = {}) => {
      // Try to use a dedicated analytics endpoint if available
      const analyticsEndpoint = "rofr-analytics";
      const params = new URLSearchParams();

      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });

      const queryString = params.toString();
      const endpoint = `${analyticsEndpoint}${queryString ? `?${queryString}` : ""}`;

      try {
        // Try the dedicated analytics endpoint first
        return await apiCall(endpoint, {}, CACHE_TTL.stats);
      } catch (error) {
        // Fallback to client-side calculation
        const data = await getROFRData({ ...filters, limit: 1000 });

        if (!data || !data.data) {
          return { entries: [], analytics: {} };
        }

        const entries = data.data;

        // Calculate analytics client-side
        const analytics = {
          totalEntries: entries.length,
          byResult: entries.reduce((acc, entry) => {
            acc[entry.result] = (acc[entry.result] || 0) + 1;
            return acc;
          }, {}),
          byResort: entries.reduce((acc, entry) => {
            acc[entry.resort] = (acc[entry.resort] || 0) + 1;
            return acc;
          }, {}),
          averagePricePerPoint:
            entries.length > 0
              ? entries.reduce(
                  (sum, entry) => sum + (entry.price_per_point || 0),
                  0,
                ) / entries.length
              : 0,
          priceRanges: {
            min: Math.min(...entries.map((e) => e.price_per_point || 0)),
            max: Math.max(...entries.map((e) => e.price_per_point || 0)),
          },
          rofrRate:
            entries.length > 0
              ? (entries.filter((e) => e.result === "taken").length /
                  entries.length) *
                100
              : 0,
        };

        return { entries, analytics };
      }
    },
    [apiCall, getROFRData],
  );

  // Optimized price trends
  const getPriceTrends = useCallback(
    async (resort = null, months = 12) => {
      // Try server-side trends endpoint first
      const trendsEndpoint = "price-trends";
      const params = new URLSearchParams();

      if (resort) params.append("resort", resort);
      params.append("months", months.toString());

      const queryString = params.toString();
      const endpoint = `${trendsEndpoint}${queryString ? `?${queryString}` : ""}`;

      try {
        return await apiCall(endpoint, {}, CACHE_TTL.stats);
      } catch (error) {
        // Fallback to client-side calculation
        const startDate = new Date();
        startDate.setMonth(startDate.getMonth() - months);

        const filters = {
          startDate: startDate.toISOString().split("T")[0],
          limit: 1000,
        };

        if (resort) {
          filters.resort = resort;
        }

        const data = await getROFRData(filters);

        if (!data || !data.data) {
          return { trends: [], summary: {} };
        }

        const entries = data.data;

        // Group by month
        const monthlyData = entries.reduce((acc, entry) => {
          if (!entry.sent_date) return acc;

          const date = new Date(entry.sent_date);
          const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

          if (!acc[monthKey]) {
            acc[monthKey] = {
              entries: [],
              total: 0,
              taken: 0,
              passed: 0,
              pending: 0,
            };
          }

          acc[monthKey].entries.push(entry);
          acc[monthKey].total++;
          acc[monthKey][entry.result]++;

          return acc;
        }, {});

        // Calculate trends
        const trends = Object.entries(monthlyData)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([month, data]) => ({
            month,
            ...data,
            averagePrice:
              data.entries.reduce(
                (sum, e) => sum + (e.price_per_point || 0),
                0,
              ) / data.entries.length,
            rofrRate: (data.taken / data.total) * 100,
          }));

        const summary = {
          totalEntries: entries.length,
          averagePrice:
            entries.reduce((sum, e) => sum + (e.price_per_point || 0), 0) /
            entries.length,
          overallROFRRate:
            (entries.filter((e) => e.result === "taken").length /
              entries.length) *
            100,
        };

        return { trends, summary };
      }
    },
    [apiCall, getROFRData],
  );

  // Dedicated price trends analysis with comprehensive filtering
  const getPriceTrendsAnalysis = useCallback(
    async (filters = {}) => {
      const params = new URLSearchParams();

      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          params.append(key, value.toString());
        }
      });

      const queryString = params.toString();
      const endpoint = `price-trends-analysis${queryString ? `?${queryString}` : ""}`;

      return await apiCall(endpoint, {}, CACHE_TTL.stats);
    },
    [apiCall],
  );

  // Multi-resort comparison with batched requests
  const getResortComparison = useCallback(
    async (resorts, timeRange = 12) => {
      if (!resorts || resorts.length === 0) {
        return {};
      }

      const startDate = new Date();
      startDate.setMonth(startDate.getMonth() - parseInt(timeRange));

      // Batch all resort data requests
      const requests = resorts.map((resort) =>
        getROFRData({
          resort,
          startDate: startDate.toISOString().split("T")[0],
          limit: 1000,
        }),
      );

      try {
        const results = await batchApiCall(requests, "resort-comparison", 100);

        const comparisonData = {};
        resorts.forEach((resort, index) => {
          if (results[index] && !results[index].error) {
            comparisonData[resort] = results[index];
          }
        });

        return comparisonData;
      } catch (error) {
        console.error("Error fetching resort comparison data:", error);
        throw error;
      }
    },
    [getROFRData, batchApiCall],
  );

  // Export functionality
  const exportROFRData = useCallback(
    async (filters = {}) => {
      const params = new URLSearchParams();

      if (filters.format) params.append("format", filters.format);
      if (filters.resort) params.append("resort", filters.resort);
      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.limit) params.append("limit", filters.limit.toString());

      const queryString = params.toString();
      const endpoint = `rofr-export${queryString ? `?${queryString}` : ""}`;

      return await apiCall(endpoint);
    },
    [apiCall],
  );

  // Utility functions
  const triggerScrape = useCallback(
    async (options = {}) => {
      return await apiCall("trigger-scrape", {
        method: "POST",
        data: options,
      });
    },
    [apiCall],
  );

  const healthCheck = useCallback(async () => {
    return await apiCall("health");
  }, [apiCall]);

  const clearCache = useCallback((pattern = null) => {
    if (pattern) {
      // Clear cache entries matching pattern
      const keysToDelete = [];
      for (const key of cache.current.keys()) {
        if (key.includes(pattern)) {
          keysToDelete.push(key);
        }
      }
      keysToDelete.forEach((key) => cache.current.delete(key));
      console.log(
        `🗑️ Cleared ${keysToDelete.length} cache entries matching "${pattern}"`,
      );
    } else {
      // Clear all cache
      const size = cache.current.size;
      cache.current.clear();
      console.log(`🗑️ Cleared all ${size} cache entries`);
    }
  }, []);

  const prefetchData = useCallback(
    async (endpoints = []) => {
      // Prefetch commonly used data
      const defaultEndpoints = ["resorts", "rofr-stats"];
      const toPrefetch = endpoints.length > 0 ? endpoints : defaultEndpoints;

      const requests = toPrefetch.map((endpoint) => {
        switch (endpoint) {
          case "resorts":
            return getResorts();
          case "usernames":
            return getUsernames();
          case "rofr-stats":
            return getROFRStats();
          default:
            return apiCall(endpoint, {}, CACHE_TTL.stats);
        }
      });

      try {
        await Promise.all(requests);
      } catch (error) {
        // Some prefetch requests failed - continue silently
      }
    },
    [getResorts, getUsernames, getROFRStats, apiCall],
  );

  const value = {
    loading,
    error,
    apiBaseUrl,

    // Core API methods
    getROFRData,
    getROFRStats,
    getResorts,
    getUsernames,
    exportROFRData,
    triggerScrape,
    healthCheck,

    // Optimized composite methods
    getDashboardData,
    getROFRAnalytics,
    getPriceTrends,
    getPriceTrendsAnalysis,
    getMonthlyStats,
    getResortComparison,

    // Utility methods
    clearCache,
    prefetchData,
    batchApiCall,
    clearError: () => setError(null),

    // Cache stats for debugging
    getCacheStats: () => ({
      size: cache.current.size,
      keys: Array.from(cache.current.keys()),
      entries: Array.from(cache.current.entries()).map(([key, entry]) => ({
        key,
        age: Date.now() - entry.timestamp,
        ttl: entry.ttl,
        expired: Date.now() - entry.timestamp > entry.ttl,
      })),
    }),

    // Check if specific data is cached
    isCached: (endpoint, params = {}) => {
      const cacheKey = getCacheKey(endpoint, params);
      return getCache(cacheKey) !== null;
    },

    // Prefetch data for specific time ranges
    prefetchTimeRange: async (timeRange) => {
      console.log(`📦 Prefetching data for time range: ${timeRange}`);
      try {
        await getDashboardData(timeRange);
        console.log(`✅ Successfully prefetched data for: ${timeRange}`);
      } catch (error) {
        console.warn(`⚠️ Failed to prefetch data for ${timeRange}:`, error);
      }
    },
  };

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
};
