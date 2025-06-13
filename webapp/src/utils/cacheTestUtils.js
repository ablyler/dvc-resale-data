/**
 * Cache testing utilities for time range functionality
 *
 * This utility helps test and debug the time range caching behavior
 * in the DVC Resale Data dashboard.
 */

/**
 * Simulates user interaction with time range switching to test caching
 * @param {Object} apiContext - The API context with cache methods
 * @param {Array} timeRanges - Array of time ranges to test
 * @returns {Object} Test results
 */
export const testTimeRangeCaching = async (apiContext, timeRanges = ['3months', '6months', '1year']) => {
  const results = {
    startTime: Date.now(),
    tests: [],
    summary: {
      totalRequests: 0,
      cacheHits: 0,
      cacheMisses: 0,
      totalTime: 0
    }
  };

  console.log('🧪 Starting time range caching test...');
  console.log(`Testing ranges: ${timeRanges.join(', ')}`);

  // Clear cache to start fresh
  apiContext.clearCache('dashboard-data');

  for (let i = 0; i < timeRanges.length; i++) {
    const timeRange = timeRanges[i];
    const testStart = Date.now();

    console.log(`\n--- Testing ${timeRange} (First load) ---`);

    // First request - should be cache miss
    const isCachedBefore = apiContext.isCached('dashboard-data', { time_range: timeRange });

    try {
      await apiContext.getDashboardData(timeRange);
      const testEnd = Date.now();
      const duration = testEnd - testStart;

      const isCachedAfter = apiContext.isCached('dashboard-data', { time_range: timeRange });

      results.tests.push({
        timeRange,
        attempt: 1,
        cachedBefore: isCachedBefore,
        cachedAfter: isCachedAfter,
        duration,
        success: true,
        type: 'first_load'
      });

      results.summary.totalRequests++;
      results.summary.totalTime += duration;

      if (isCachedBefore) {
        results.summary.cacheHits++;
      } else {
        results.summary.cacheMisses++;
      }

      console.log(`✅ First load completed in ${duration}ms`);
      console.log(`   Cached before: ${isCachedBefore}, Cached after: ${isCachedAfter}`);

    } catch (error) {
      results.tests.push({
        timeRange,
        attempt: 1,
        error: error.message,
        success: false,
        type: 'first_load'
      });
      console.log(`❌ First load failed: ${error.message}`);
    }
  }

  // Test switching back to previously loaded ranges (should be cache hits)
  console.log('\n🔄 Testing cache hits by switching back to previous ranges...');

  for (let i = 0; i < timeRanges.length; i++) {
    const timeRange = timeRanges[i];
    const testStart = Date.now();

    console.log(`\n--- Testing ${timeRange} (Cache hit test) ---`);

    const isCachedBefore = apiContext.isCached('dashboard-data', { time_range: timeRange });

    try {
      await apiContext.getDashboardData(timeRange);
      const testEnd = Date.now();
      const duration = testEnd - testStart;

      results.tests.push({
        timeRange,
        attempt: 2,
        cachedBefore: isCachedBefore,
        duration,
        success: true,
        type: 'cache_test'
      });

      results.summary.totalRequests++;
      results.summary.totalTime += duration;

      if (isCachedBefore) {
        results.summary.cacheHits++;
        console.log(`🎯 Cache hit! Loaded in ${duration}ms`);
      } else {
        results.summary.cacheMisses++;
        console.log(`🔄 Cache miss (unexpected) - loaded in ${duration}ms`);
      }

    } catch (error) {
      results.tests.push({
        timeRange,
        attempt: 2,
        error: error.message,
        success: false,
        type: 'cache_test'
      });
      console.log(`❌ Cache test failed: ${error.message}`);
    }
  }

  results.endTime = Date.now();
  results.summary.totalTestTime = results.endTime - results.startTime;

  // Print summary
  console.log('\n📊 Test Summary:');
  console.log('================');
  console.log(`Total requests: ${results.summary.totalRequests}`);
  console.log(`Cache hits: ${results.summary.cacheHits}`);
  console.log(`Cache misses: ${results.summary.cacheMisses}`);
  console.log(`Hit rate: ${((results.summary.cacheHits / results.summary.totalRequests) * 100).toFixed(1)}%`);
  console.log(`Total API time: ${results.summary.totalTime}ms`);
  console.log(`Total test time: ${results.summary.totalTestTime}ms`);
  console.log(`Average request time: ${(results.summary.totalTime / results.summary.totalRequests).toFixed(1)}ms`);

  return results;
};

/**
 * Monitors cache behavior during normal dashboard usage
 * @param {Object} apiContext - The API context with cache methods
 * @returns {Function} Cleanup function to stop monitoring
 */
export const monitorCacheBehavior = (apiContext) => {
  const originalGetDashboardData = apiContext.getDashboardData;
  const stats = {
    requests: 0,
    cacheHits: 0,
    cacheMisses: 0,
    timeRangeStats: {}
  };

  // Wrap the getDashboardData method to track usage
  apiContext.getDashboardData = async (timeRange = '3months') => {
    const startTime = Date.now();
    const wasCached = apiContext.isCached('dashboard-data', { time_range: timeRange });

    stats.requests++;
    if (wasCached) {
      stats.cacheHits++;
    } else {
      stats.cacheMisses++;
    }

    if (!stats.timeRangeStats[timeRange]) {
      stats.timeRangeStats[timeRange] = { requests: 0, hits: 0, misses: 0 };
    }

    stats.timeRangeStats[timeRange].requests++;
    if (wasCached) {
      stats.timeRangeStats[timeRange].hits++;
    } else {
      stats.timeRangeStats[timeRange].misses++;
    }

    console.log(`📈 Dashboard data request for ${timeRange}: ${wasCached ? 'CACHE HIT' : 'CACHE MISS'}`);

    const result = await originalGetDashboardData(timeRange);
    const endTime = Date.now();

    console.log(`⏱️  Request completed in ${endTime - startTime}ms`);

    return result;
  };

  // Return cleanup function
  return () => {
    apiContext.getDashboardData = originalGetDashboardData;

    console.log('\n📊 Cache Monitoring Summary:');
    console.log('=============================');
    console.log(`Total requests: ${stats.requests}`);
    console.log(`Cache hits: ${stats.cacheHits} (${((stats.cacheHits / stats.requests) * 100).toFixed(1)}%)`);
    console.log(`Cache misses: ${stats.cacheMisses} (${((stats.cacheMisses / stats.requests) * 100).toFixed(1)}%)`);
    console.log('\nPer time range:');

    Object.entries(stats.timeRangeStats).forEach(([range, rangeStats]) => {
      const hitRate = (rangeStats.hits / rangeStats.requests) * 100;
      console.log(`  ${range}: ${rangeStats.requests} requests, ${hitRate.toFixed(1)}% hit rate`);
    });

    return stats;
  };
};

/**
 * Validates that cache keys are properly formatted for time ranges
 * @param {Object} cacheStats - Cache statistics from getCacheStats()
 */
export const validateCacheKeys = (cacheStats) => {
  console.log('🔍 Validating cache keys...');

  const dashboardKeys = cacheStats.keys.filter(key => key.startsWith('dashboard-data:'));
  const validTimeRanges = ['3months', '6months', '1year'];

  console.log(`Found ${dashboardKeys.length} dashboard cache keys:`);

  dashboardKeys.forEach(key => {
    console.log(`  ${key}`);

    // Extract time range from key
    const match = key.match(/time_range":"([^"]+)"/);
    if (match) {
      const timeRange = match[1];
      if (validTimeRanges.includes(timeRange)) {
        console.log(`    ✅ Valid time range: ${timeRange}`);
      } else {
        console.log(`    ⚠️  Unknown time range: ${timeRange}`);
      }
    } else {
      console.log(`    ❌ Could not extract time range from key`);
    }
  });

  const uniqueTimeRanges = [...new Set(dashboardKeys.map(key => {
    const match = key.match(/time_range":"([^"]+)"/);
    return match ? match[1] : null;
  }).filter(Boolean))];

  console.log(`\nUnique time ranges cached: ${uniqueTimeRanges.join(', ')}`);

  return {
    totalDashboardKeys: dashboardKeys.length,
    uniqueTimeRanges,
    validKeys: dashboardKeys.filter(key => {
      const match = key.match(/time_range":"([^"]+)"/);
      return match && validTimeRanges.includes(match[1]);
    }).length
  };
};

/**
 * Performance test for cache vs fresh data loading
 * @param {Object} apiContext - The API context
 * @param {string} timeRange - Time range to test
 * @param {number} iterations - Number of test iterations
 */
export const performanceTest = async (apiContext, timeRange = '3months', iterations = 5) => {
  console.log(`🏁 Performance test: ${timeRange} (${iterations} iterations)`);

  const results = {
    fresh: [],
    cached: []
  };

  // Test fresh loads
  for (let i = 0; i < iterations; i++) {
    apiContext.clearCache('dashboard-data');

    const start = Date.now();
    await apiContext.getDashboardData(timeRange);
    const duration = Date.now() - start;

    results.fresh.push(duration);
    console.log(`Fresh load ${i + 1}: ${duration}ms`);
  }

  // Test cached loads
  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    await apiContext.getDashboardData(timeRange);
    const duration = Date.now() - start;

    results.cached.push(duration);
    console.log(`Cached load ${i + 1}: ${duration}ms`);
  }

  const avgFresh = results.fresh.reduce((a, b) => a + b, 0) / results.fresh.length;
  const avgCached = results.cached.reduce((a, b) => a + b, 0) / results.cached.length;
  const speedup = avgFresh / avgCached;

  console.log('\n📊 Performance Results:');
  console.log(`Average fresh load: ${avgFresh.toFixed(1)}ms`);
  console.log(`Average cached load: ${avgCached.toFixed(1)}ms`);
  console.log(`Cache speedup: ${speedup.toFixed(1)}x faster`);

  return {
    fresh: results.fresh,
    cached: results.cached,
    averages: { fresh: avgFresh, cached: avgCached },
    speedup
  };
};
