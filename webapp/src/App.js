import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { Box } from "@mui/material";

import AppNavigation from "./components/AppNavigation";
import Dashboard from "./pages/Dashboard";
import ROFRAnalytics from "./pages/ROFRAnalytics";
import PriceTrends from "./pages/PriceTrends";
import ResortComparison from "./pages/ResortComparison";
import DataExplorer from "./pages/DataExplorer";
import { ApiProvider } from "./context/ApiContext";

// Create MUI theme with DVC-inspired colors
const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2", // DVC blue
      light: "#42a5f5",
      dark: "#1565c0",
    },
    secondary: {
      main: "#f57c00", // DVC gold/orange
      light: "#ffb74d",
      dark: "#e65100",
    },
    background: {
      default: "#f5f5f5",
      paper: "#ffffff",
    },
    success: {
      main: "#4caf50", // For "passed" ROFR
    },
    error: {
      main: "#f44336", // For "taken" ROFR
    },
    warning: {
      main: "#ff9800", // For "pending" ROFR
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          borderRadius: 8,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ApiProvider>
        <Router
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Box sx={{ display: "flex", minHeight: "100vh" }}>
            <AppNavigation />
            <Box
              component="main"
              sx={{
                flexGrow: 1,
                p: { xs: 1, sm: 2, md: 3 },
                mt: { xs: 7, sm: 0 },
                backgroundColor: "background.default",
                minHeight: "100vh",
                width: "100%",
              }}
            >
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/rofr-analytics" element={<ROFRAnalytics />} />
                <Route path="/price-trends" element={<PriceTrends />} />
                <Route
                  path="/price-trends-original"
                  element={<PriceTrends />}
                />
                <Route
                  path="/resort-comparison"
                  element={<ResortComparison />}
                />
                <Route path="/data-explorer" element={<DataExplorer />} />
              </Routes>
            </Box>
          </Box>
        </Router>
      </ApiProvider>
    </ThemeProvider>
  );
}

export default App;
