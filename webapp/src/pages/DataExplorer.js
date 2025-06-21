import React, { useState, useEffect, useCallback, useRef } from "react";
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
  TablePagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  ButtonGroup,
} from "@mui/material";
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  Clear as ClearIcon,
  Sort as SortIcon,
} from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useApi } from "../context/ApiContext";
import UsernameSelect from "../components/form/UsernameSelect";

const DataExplorer = () => {
  const apiContext = useApi();

  // State for component initialization
  const [isInitialized, setIsInitialized] = useState(false);
  const [initError, setInitError] = useState(null);

  // Basic states
  const [data, setData] = useState([]);
  const [resorts, setResorts] = useState([]);
  const [loadingData, setLoadingData] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [sortBy, setSortBy] = useState("");
  const [sortOrder, setSortOrder] = useState("desc");
  const [activeTab, setActiveTab] = useState(0);

  // Filter states - initialize with safer default values
  const [filters, setFilters] = useState(() => {
    const defaultFilters = {
      resort: "",
      result: "",
      startDate: null,
      endDate: null,
      username: "",
      minPrice: "",
      maxPrice: "",
      minPoints: "",
      maxPoints: "",
      useYear: "",
      priceRange: [0, 300],
      pointsRange: [0, 1000],
    };
    return defaultFilters;
  });

  // Advanced filters
  const [advancedFilters, setAdvancedFilters] = useState(() => {
    const defaultAdvancedFilters = {
      showOnlyRecent: false,
      excludePending: false,
      onlyROFRTaken: false,
      highValueContracts: false,
    };
    return defaultAdvancedFilters;
  });

  // UI states
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState("csv");
  const [selectedColumns, setSelectedColumns] = useState([
    "sent_date",
    "resort",
    "username",
    "price_per_point",
    "points",
    "points_details",
    "use_year",
    "result",
    "result_date",
  ]);

  // Debounce timer for filters
  const debounceTimer = useRef(null);
  const [debouncedFilters, setDebouncedFilters] = useState(filters);

  // Debounce filter changes to prevent constant re-fetching
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = setTimeout(() => {
      setDebouncedFilters(filters);
    }, 300); // 300ms debounce delay

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [filters]);

  // Extract API methods safely
  const { getROFRData, getResorts, exportROFRData, error, prefetchData } =
    apiContext || {};

  const availableColumns = [
    { key: "sent_date", label: "Date Sent" },
    { key: "result_date", label: "Result Date" },
    { key: "resort", label: "Resort" },
    { key: "resort_name", label: "Resort Name" },
    { key: "username", label: "Username" },
    { key: "price_per_point", label: "Price/Point" },
    { key: "total_cost", label: "Total Cost" },
    { key: "points", label: "Points" },
    { key: "use_year", label: "Use Year" },
    { key: "points_details", label: "Points Details" },
    { key: "result", label: "Status" },
    { key: "thread_url", label: "Thread URL" },
    { key: "raw_entry", label: "Raw Entry" },
  ];

  const useYears = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  // Initialize component
  useEffect(() => {
    const initializeComponent = async () => {
      try {
        // Prefetch resorts and usernames data on component mount for better performance
        if (prefetchData) {
          await prefetchData(["resorts", "usernames"]);
        }
        if (getResorts) {
          const resortsData = await getResorts();
          setResorts(resortsData?.data || []);
        }

        setIsInitialized(true);
      } catch (err) {
        console.error("Error initializing component:", err);
        setInitError(err.message);
        setResorts([]);
      }
    };

    initializeComponent();
  }, [getResorts, prefetchData]);

  const buildFilterParams = useCallback(() => {
    const params = {};

    // Use debounced filters instead of direct filters
    const filtersToUse = debouncedFilters;

    // Ensure filters is defined and is an object
    if (!filtersToUse || typeof filtersToUse !== "object") return params;

    // Basic filters - use safe property access
    if (filtersToUse.resort && typeof filtersToUse.resort === "string")
      params.resort = filtersToUse.resort;
    if (filtersToUse.result && typeof filtersToUse.result === "string")
      params.result = filtersToUse.result;
    if (filtersToUse.username && typeof filtersToUse.username === "string")
      params.username = filtersToUse.username;
    if (filtersToUse.useYear && typeof filtersToUse.useYear === "string")
      params.use_year = filtersToUse.useYear;

    // Date filters - ensure dates are valid
    if (filtersToUse.startDate && filtersToUse.startDate instanceof Date) {
      params.start_date = filtersToUse.startDate.toISOString().split("T")[0];
    }
    if (filtersToUse.endDate && filtersToUse.endDate instanceof Date) {
      params.end_date = filtersToUse.endDate.toISOString().split("T")[0];
    }

    // Price filters - ensure valid numbers
    if (filtersToUse.minPrice && !isNaN(parseFloat(filtersToUse.minPrice))) {
      params.min_price = parseFloat(filtersToUse.minPrice);
    }
    if (filtersToUse.maxPrice && !isNaN(parseFloat(filtersToUse.maxPrice))) {
      params.max_price = parseFloat(filtersToUse.maxPrice);
    }

    // Points filters - ensure valid numbers
    if (filtersToUse.minPoints && !isNaN(parseInt(filtersToUse.minPoints))) {
      params.min_points = parseInt(filtersToUse.minPoints);
    }
    if (filtersToUse.maxPoints && !isNaN(parseInt(filtersToUse.maxPoints))) {
      params.max_points = parseInt(filtersToUse.maxPoints);
    }

    // Advanced filters
    if (advancedFilters.showOnlyRecent) {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      params.start_date = thirtyDaysAgo.toISOString().split("T")[0];
    }

    if (advancedFilters.excludePending) {
      params.exclude_result = "pending";
    }

    if (advancedFilters.onlyROFRTaken) {
      params.result = "taken";
    }

    if (advancedFilters.highValueContracts) {
      params.min_total_cost = 50000;
    }

    // Add sorting parameters - always include sort parameters
    params.sort_by = sortBy || "sent_date";
    params.sort_order = sortOrder || "desc";

    return params;
  }, [debouncedFilters, advancedFilters, sortBy, sortOrder]);

  const fetchData = useCallback(async () => {
    if (!getROFRData) {
      return;
    }

    setLoadingData(true);
    try {
      const filterParams = buildFilterParams();
      const response = await getROFRData({
        ...filterParams,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });

      // Handle the API response format - check for data in multiple locations
      let dataArray = null;
      let totalCount = 0;

      if (response?.entries && Array.isArray(response.entries)) {
        // First priority: entries array (processed by ApiContext)
        dataArray = response.entries;
        totalCount =
          response.total_count ||
          response.count ||
          response.meta?.count ||
          response.entries.length;
      } else if (response?.data && Array.isArray(response.data)) {
        // Second priority: direct data array
        dataArray = response.data;
        totalCount =
          response.total_count ||
          response.count ||
          response.total ||
          response.data.length;
      } else if (
        response?.data?.entries &&
        Array.isArray(response.data.entries)
      ) {
        // Third priority: nested entries
        dataArray = response.data.entries;
        totalCount =
          response.data.total_count ||
          response.data.count ||
          response.data.entries.length;
      }

      if (dataArray && dataArray.length > 0) {
        // Data is already sorted by the server, no need for client-side sorting
        setData(dataArray);
        setTotalCount(totalCount);
      } else {
        setData([]);
        setTotalCount(0);
      }
    } catch (err) {
      console.error("Error fetching data:", err);
      setData([]);
      setTotalCount(0);
    } finally {
      setLoadingData(false);
    }
  }, [getROFRData, rowsPerPage, page, buildFilterParams]);

  // Define callbacks before early return
  const handleFilterChange = useCallback((field, value) => {
    setFilters((prev) => {
      // Ensure prev is a valid object before spreading
      const safePrev =
        prev && typeof prev === "object" && !Array.isArray(prev) ? prev : {};
      const newFilters = {
        ...safePrev,
        [field]: value,
      };
      return newFilters;
    });
  }, []);

  // Create a stable callback for username change handler
  const handleUsernameChange = useCallback((value) => {
    setFilters((prev) => {
      const safePrev =
        prev && typeof prev === "object" && !Array.isArray(prev) ? prev : {};
      return {
        ...safePrev,
        username: value,
      };
    });
  }, []);

  const handleAdvancedFilterChange = useCallback((field, value) => {
    setAdvancedFilters((prev) => {
      // Ensure prev is a valid object before spreading
      const safePrev =
        prev && typeof prev === "object" && !Array.isArray(prev) ? prev : {};
      return {
        ...safePrev,
        [field]: value,
      };
    });
  }, []);

  useEffect(() => {
    if (isInitialized && !initError) {
      fetchData();
    }
  }, [
    page,
    rowsPerPage,
    sortBy,
    sortOrder,
    isInitialized,
    initError,
    fetchData,
  ]);

  // Separate effect for filter changes to avoid unnecessary re-renders
  useEffect(() => {
    if (isInitialized && !initError && getROFRData && buildFilterParams) {
      setPage(0); // Reset to first page when filters change

      // Call fetchData manually to avoid dependency loops
      const fetchFilteredData = async () => {
        setLoadingData(true);
        try {
          const filterParams = buildFilterParams();
          const response = await getROFRData({
            ...filterParams,
            limit: rowsPerPage,
            offset: 0, // Always start from 0 when filters change
          });

          // Handle the API response format
          let dataArray = null;
          let totalCount = 0;

          if (response?.entries && Array.isArray(response.entries)) {
            dataArray = response.entries;
            totalCount =
              response.total_count ||
              response.count ||
              response.meta?.count ||
              response.entries.length;
          } else if (response?.data && Array.isArray(response.data)) {
            dataArray = response.data;
            totalCount =
              response.total_count ||
              response.count ||
              response.total ||
              response.data.length;
          } else if (
            response?.data?.entries &&
            Array.isArray(response.data.entries)
          ) {
            dataArray = response.data.entries;
            totalCount =
              response.data.total_count ||
              response.data.count ||
              response.data.entries.length;
          }

          if (dataArray && dataArray.length > 0) {
            setData(dataArray);
            setTotalCount(totalCount);
          } else {
            setData([]);
            setTotalCount(0);
          }
        } catch (err) {
          console.error("Error fetching filtered data:", err);
          setData([]);
          setTotalCount(0);
        } finally {
          setLoadingData(false);
        }
      };

      fetchFilteredData();
    }
  }, [
    debouncedFilters,
    advancedFilters,
    isInitialized,
    initError,
    getROFRData,
    buildFilterParams,
    rowsPerPage,
  ]);

  // Early return if API context is not available (after all hooks)
  if (!apiContext) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          API context is not available. Please ensure the component is wrapped
          in ApiProvider.
        </Alert>
      </Box>
    );
  }

  const handleApplyFilters = () => {
    setPage(0);
    fetchData();
  };

  const handleClearFilters = () => {
    const defaultFilters = {
      resort: "",
      result: "",
      startDate: null,
      endDate: null,
      username: "",
      minPrice: "",
      maxPrice: "",
      minPoints: "",
      maxPoints: "",
      useYear: "",
      priceRange: [0, 300],
      pointsRange: [0, 1000],
    };
    const defaultAdvancedFilters = {
      showOnlyRecent: false,
      excludePending: false,
      onlyROFRTaken: false,
      highValueContracts: false,
    };

    setFilters(defaultFilters);
    setAdvancedFilters(defaultAdvancedFilters);
    setPage(0);
    setTimeout(() => fetchData(), 100);
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  };

  const handleExport = async () => {
    if (!exportROFRData) {
      console.error("Export function not available");
      return;
    }

    try {
      const filterParams = buildFilterParams();
      const response = await exportROFRData({
        ...filterParams,
        format: exportFormat,
        columns: selectedColumns,
      });

      // Handle download based on format
      if (exportFormat === "csv" && response) {
        const blob = new Blob([response], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = `rofr_data_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      }

      setExportDialogOpen(false);
    } catch (err) {
      console.error("Export error:", err);
    }
  };

  const getStatusChip = (status) => {
    const colors = {
      passed: "success",
      taken: "error",
      pending: "warning",
    };

    return (
      <Chip
        label={status}
        size="small"
        color={colors[status] || "default"}
        variant="outlined"
      />
    );
  };

  const formatCurrency = (value) => {
    if (!value) return "N/A";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-US", {
      timeZone: "UTC",
    });
  };

  const DataTable = () => (
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
          <Typography variant="h6">ROFR Data Explorer</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button
              startIcon={<RefreshIcon />}
              onClick={fetchData}
              disabled={loadingData}
              size="small"
            >
              Refresh
            </Button>
            <Button
              startIcon={<DownloadIcon />}
              onClick={() => setExportDialogOpen(true)}
              variant="outlined"
              size="small"
            >
              Export
            </Button>
          </Box>
        </Box>

        {loadingData && <CircularProgress size={24} sx={{ mb: 2 }} />}

        <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                {selectedColumns.map((columnKey) => {
                  const column = availableColumns.find(
                    (col) => col.key === columnKey,
                  );
                  if (!column) return null;

                  return (
                    <TableCell key={columnKey}>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        {column.label}
                        {[
                          "sent_date",
                          "price_per_point",
                          "total_cost",
                          "points",
                        ].includes(columnKey) && (
                          <IconButton
                            size="small"
                            onClick={() => handleSort(columnKey)}
                            color={sortBy === columnKey ? "primary" : "default"}
                          >
                            <SortIcon fontSize="small" />
                          </IconButton>
                        )}
                      </Box>
                    </TableCell>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {(() => {
                if (!data || !Array.isArray(data) || data.length === 0) {
                  return (
                    <TableRow>
                      <TableCell
                        colSpan={selectedColumns.length}
                        align="center"
                      >
                        {loadingData ? "Loading..." : "No data available"}
                      </TableCell>
                    </TableRow>
                  );
                }

                return data.map((entry, index) => (
                  <TableRow key={`row-${index}`} hover>
                    {selectedColumns.map((columnKey) => {
                      const column = availableColumns.find(
                        (col) => col.key === columnKey,
                      );
                      if (!column) return null;

                      let cellContent;
                      try {
                        switch (columnKey) {
                          case "sent_date":
                          case "result_date":
                            cellContent = formatDate(entry[columnKey]);
                            break;
                          case "price_per_point":
                            cellContent = entry[columnKey]
                              ? `$${parseFloat(entry[columnKey]).toFixed(2)}`
                              : "N/A";
                            break;
                          case "total_cost":
                            cellContent = formatCurrency(entry[columnKey]);
                            break;
                          case "result":
                            cellContent = getStatusChip(entry[columnKey]);
                            break;
                          case "points":
                            cellContent =
                              entry[columnKey]?.toLocaleString() || "N/A";
                            break;
                          case "thread_url":
                            cellContent = entry[columnKey] ? (
                              <Button
                                size="small"
                                onClick={() =>
                                  window.open(entry[columnKey], "_blank")
                                }
                              >
                                View
                              </Button>
                            ) : (
                              "N/A"
                            );
                            break;
                          case "raw_entry":
                            cellContent = entry[columnKey] ? (
                              <Typography
                                variant="body2"
                                sx={{
                                  maxWidth: 300,
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  cursor: "pointer",
                                }}
                                title={entry[columnKey]}
                              >
                                {entry[columnKey]}
                              </Typography>
                            ) : (
                              "N/A"
                            );
                            break;
                          default:
                            cellContent = entry[columnKey] || "N/A";
                        }
                      } catch (error) {
                        cellContent = "Error";
                      }

                      return (
                        <TableCell key={`${columnKey}-${index}`}>
                          {cellContent}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ));
              })()}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={totalCount}
          page={page}
          onPageChange={(event, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(event) => {
            setRowsPerPage(parseInt(event.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </CardContent>
    </Card>
  );

  const FiltersPanel = () => (
    <Accordion
      expanded={filtersExpanded}
      onChange={() => setFiltersExpanded(!filtersExpanded)}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <FilterIcon color="primary" />
          <Typography variant="h6">Filters & Search</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Grid container spacing={2}>
          {/* Basic Filters */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Basic Filters
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
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

          <Grid item xs={12} sm={6} md={3}>
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

          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Use Year</InputLabel>
              <Select
                value={filters.useYear}
                onChange={(e) => handleFilterChange("useYear", e.target.value)}
                label="Use Year"
              >
                <MenuItem value="">All Use Years</MenuItem>
                {useYears.map((month) => (
                  <MenuItem key={month} value={month}>
                    {month}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <UsernameSelect
              key="stable-username-input"
              label="Username"
              value={filters.username || ""}
              onChange={handleUsernameChange}
              size="small"
              fullWidth
              placeholder="Select username"
            />
          </Grid>

          {/* Date Filters */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Date Range
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Start Date"
                value={filters.startDate}
                onChange={(date) => handleFilterChange("startDate", date)}
                slots={{
                  textField: TextField,
                }}
                slotProps={{
                  textField: {
                    size: "small",
                    fullWidth: true,
                  },
                }}
              />
            </LocalizationProvider>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="End Date"
                value={filters.endDate}
                onChange={(date) => handleFilterChange("endDate", date)}
                slots={{
                  textField: TextField,
                }}
                slotProps={{
                  textField: {
                    size: "small",
                    fullWidth: true,
                  },
                }}
              />
            </LocalizationProvider>
          </Grid>

          {/* Price Filters */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Price Range ($/point)
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Min Price"
              type="number"
              value={filters.minPrice}
              onChange={(e) => handleFilterChange("minPrice", e.target.value)}
              size="small"
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Max Price"
              type="number"
              value={filters.maxPrice}
              onChange={(e) => handleFilterChange("maxPrice", e.target.value)}
              size="small"
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />
          </Grid>

          {/* Points Filters */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Points Range
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Min Points"
              type="number"
              value={filters.minPoints}
              onChange={(e) => handleFilterChange("minPoints", e.target.value)}
              size="small"
              fullWidth
              inputProps={{ min: 0, step: 1 }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Max Points"
              type="number"
              value={filters.maxPoints}
              onChange={(e) => handleFilterChange("maxPoints", e.target.value)}
              size="small"
              fullWidth
              inputProps={{ min: 0, step: 1 }}
            />
          </Grid>

          {/* Advanced Filters */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Advanced Filters
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={advancedFilters.showOnlyRecent}
                  onChange={(e) =>
                    handleAdvancedFilterChange(
                      "showOnlyRecent",
                      e.target.checked,
                    )
                  }
                />
              }
              label="Recent Only (30 days)"
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={advancedFilters.excludePending}
                  onChange={(e) =>
                    handleAdvancedFilterChange(
                      "excludePending",
                      e.target.checked,
                    )
                  }
                />
              }
              label="Exclude Pending"
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={advancedFilters.onlyROFRTaken}
                  onChange={(e) =>
                    handleAdvancedFilterChange(
                      "onlyROFRTaken",
                      e.target.checked,
                    )
                  }
                />
              }
              label="ROFR Taken Only"
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={advancedFilters.highValueContracts}
                  onChange={(e) =>
                    handleAdvancedFilterChange(
                      "highValueContracts",
                      e.target.checked,
                    )
                  }
                />
              }
              label="High Value ($50k+)"
            />
          </Grid>

          {/* Action Buttons */}
          <Grid item xs={12}>
            <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
              <Button
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={handleApplyFilters}
                disabled={loadingData}
              >
                Apply Filters
              </Button>
              <Button
                variant="outlined"
                startIcon={<ClearIcon />}
                onClick={handleClearFilters}
              >
                Clear All
              </Button>
            </Box>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );

  const ExportDialog = () => (
    <Dialog
      open={exportDialogOpen}
      onClose={() => setExportDialogOpen(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>Export Data</DialogTitle>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth sx={{ mt: 1 }}>
              <InputLabel>Export Format</InputLabel>
              <Select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                label="Export Format"
              >
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="json">JSON</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Select Columns to Export
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              {availableColumns.map((column) => (
                <Chip
                  key={column.key}
                  label={column.label}
                  clickable
                  color={
                    selectedColumns.includes(column.key) ? "primary" : "default"
                  }
                  onClick={() => {
                    if (selectedColumns.includes(column.key)) {
                      setSelectedColumns((prev) =>
                        prev.filter((col) => col !== column.key),
                      );
                    } else {
                      setSelectedColumns((prev) => [...prev, column.key]);
                    }
                  }}
                />
              ))}
            </Box>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
        <Button
          onClick={handleExport}
          variant="contained"
          disabled={selectedColumns.length === 0}
        >
          Export
        </Button>
      </DialogActions>
    </Dialog>
  );

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );

  // Handle initialization errors
  if (initError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error initializing Data Explorer: {initError}
        </Alert>
      </Box>
    );
  }

  // Handle API context not available
  if (!apiContext) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          API context not available. Please refresh the page.
        </Alert>
      </Box>
    );
  }

  // Show loading state while initializing
  if (!isInitialized) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Initializing Data Explorer...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Error loading data explorer: {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        Data Explorer
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Advanced data exploration and export tools for resale data
      </Typography>

      {/* Filters */}
      <Box sx={{ mb: 3 }}>
        <FiltersPanel />
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
        >
          <Tab label={`Data Table (${totalCount.toLocaleString()})`} />
          <Tab label="Column Manager" />
          <Tab label="Export Options" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={activeTab} index={0}>
        <DataTable />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Manage Table Columns
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Select which columns to display in the data table
            </Typography>

            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
              {availableColumns.map((column) => (
                <Chip
                  key={column.key}
                  label={column.label}
                  clickable
                  color={
                    selectedColumns.includes(column.key) ? "primary" : "default"
                  }
                  variant={
                    selectedColumns.includes(column.key) ? "filled" : "outlined"
                  }
                  onClick={() => {
                    if (selectedColumns.includes(column.key)) {
                      setSelectedColumns((prev) =>
                        prev.filter((col) => col !== column.key),
                      );
                    } else {
                      setSelectedColumns((prev) => [...prev, column.key]);
                    }
                  }}
                />
              ))}
            </Box>

            <Box sx={{ mt: 3, display: "flex", gap: 1 }}>
              <Button
                variant="outlined"
                onClick={() =>
                  setSelectedColumns(availableColumns.map((col) => col.key))
                }
              >
                Select All
              </Button>
              <Button
                variant="outlined"
                onClick={() =>
                  setSelectedColumns([
                    "sent_date",
                    "resort",
                    "price_per_point",
                    "result",
                  ])
                }
              >
                Essential Only
              </Button>
              <Button variant="outlined" onClick={() => setSelectedColumns([])}>
                Clear All
              </Button>
            </Box>
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Export Configuration
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Export Formats
                </Typography>
                <ButtonGroup variant="outlined">
                  <Button
                    variant={exportFormat === "csv" ? "contained" : "outlined"}
                    onClick={() => setExportFormat("csv")}
                  >
                    CSV
                  </Button>
                  <Button
                    variant={exportFormat === "json" ? "contained" : "outlined"}
                    onClick={() => setExportFormat("json")}
                  >
                    JSON
                  </Button>
                </ButtonGroup>
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  startIcon={<DownloadIcon />}
                  onClick={() => setExportDialogOpen(true)}
                  size="large"
                >
                  Configure & Export
                </Button>
              </Grid>
            </Grid>

            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                Export functionality will apply current filters and column
                selections. Large exports may take a few moments to complete.
              </Typography>
            </Alert>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Export Dialog */}
      <ExportDialog />
    </Box>
  );
};

export default DataExplorer;
