import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Autocomplete, TextField, CircularProgress, Chip } from "@mui/material";
import { useApi } from "../../context/ApiContext";

const UsernameSelect = React.memo(
  ({
    value,
    onChange,
    multiple = false,
    placeholder = "Select username(s)",
    size = "small",
    fullWidth = true,
    ...props
  }) => {
    const { getUsernames } = useApi();
    const [usernames, setUsernames] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Fetch usernames on component mount
    useEffect(() => {
      const fetchUsernames = async () => {
        if (!getUsernames) return;

        setLoading(true);
        setError(null);
        try {
          const response = await getUsernames();
          const usernameList = response?.data || response || [];

          // Ensure we always have an array
          if (Array.isArray(usernameList)) {
            setUsernames(usernameList);
            setError(null);
          } else {
            console.warn("Invalid usernames data received:", usernameList);
            setUsernames([]);
            setError("Invalid data format received");
          }
        } catch (err) {
          console.error("Error fetching usernames:", err);
          setError("Failed to load usernames");
          setUsernames([]);
        } finally {
          setLoading(false);
        }
      };

      fetchUsernames();
    }, [getUsernames]);

    // Handle value changes
    const handleChange = useCallback(
      (event, newValue) => {
        if (multiple) {
          // For multiple selection, newValue is an array
          onChange(newValue);
        } else {
          // For single selection, newValue is a string or null
          onChange(newValue || "");
        }
      },
      [onChange, multiple],
    );

    // Memoize options for performance
    const options = useMemo(() => {
      if (!Array.isArray(usernames)) {
        console.warn("Usernames is not an array:", usernames);
        return [];
      }
      return usernames.filter(
        (username) =>
          username && typeof username === "string" && username.trim(),
      );
    }, [usernames]);

    // Format the current value for display
    const displayValue = useMemo(() => {
      if (multiple) {
        return Array.isArray(value) ? value : value ? [value] : [];
      } else {
        return value || null;
      }
    }, [value, multiple]);

    // Custom render for multiple selection
    const renderTags = useCallback((tagValue, getTagProps) => {
      return tagValue.map((option, index) => (
        <Chip
          key={option}
          label={option}
          size="small"
          {...getTagProps({ index })}
        />
      ));
    }, []);

    return (
      <Autocomplete
        {...props}
        options={options}
        value={displayValue}
        onChange={handleChange}
        multiple={multiple}
        loading={loading}
        disabled={loading || error}
        freeSolo={false}
        autoComplete
        autoHighlight
        autoSelect={false}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        size={size}
        fullWidth={fullWidth}
        renderTags={multiple ? renderTags : undefined}
        renderInput={(params) => (
          <TextField
            {...params}
            placeholder={placeholder}
            error={!!error}
            helperText={error}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {loading ? (
                    <CircularProgress color="inherit" size={20} />
                  ) : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
        renderOption={(props, option) => (
          <li {...props} key={option}>
            {option}
          </li>
        )}
        isOptionEqualToValue={(option, value) => option === value}
        getOptionLabel={(option) => option || ""}
      />
    );
  },
);

UsernameSelect.displayName = "UsernameSelect";

export default UsernameSelect;
