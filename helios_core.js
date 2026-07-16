/**
 * @file helios_core.js - Core data management and preprocessing logic for HELIOS 2.0
 * Handles CSV parsing, data transformations, column operations, and state management.
 * 
 * @author HELIOS Team
 * @version 2.0.0
 */

// --- GLOBAL STATE MANAGEMENT ---
// Centralized state object for the application
const HeliosState = {
    tableData: {
        headers: [],
        rows: []
    },
    datasetDescriptionText: '',
    targetColumnIndex: null,
    comparisonColumnIndices: [],
    isDataDiscretized: false,
    collapsibleStates: {},
    
    // Chart instances for cleanup
    analysisChartInstance: null,
    summaryNumericChartInstance: null,
    summaryCategoricalChartInstance: null
};

// --- APPLICATION NAMESPACE INITIALIZATION ---
if (!window.hypothesesApp) {
    window.hypothesesApp = {};
}

window.hypothesesApp.categorizedHypotheses = {};
window.hypothesesApp.displayCounts = {};

// --- CSV PARSING UTILITIES ---

/**
 * Parses a single row of a CSV string, correctly handling quoted fields and escaped quotes.
 * @param {string} rowString - The string for a single CSV row.
 * @param {string} delimiter - The delimiter character (e.g., ',' or ';').
 * @returns {string[]} An array of strings representing the cells in the row.
 */
function robustParseCSVRow(rowString, delimiter) {
    const cells = [];
    let inQuotes = false;
    let currentCell = '';
    
    for (let i = 0; i < rowString.length; i++) {
        const char = rowString[i];
        
        if (inQuotes) {
            if (char === '"') {
                if (i + 1 < rowString.length && rowString[i + 1] === '"') {
                    currentCell += '"';
                    i++;
                } else {
                    inQuotes = false;
                }
            } else {
                currentCell += char;
            }
        } else {
            if (char === '"') {
                inQuotes = true;
            } else if (char === delimiter) {
                cells.push(currentCell);
                currentCell = '';
            } else {
                currentCell += char;
            }
        }
    }
    cells.push(currentCell);
    return cells.map(cell => cell.trim());
}

/**
 * Handles CSV file loading and parsing.
 * @param {File} file - The CSV file to parse.
 * @param {Function} callback - Callback function to execute after successful parsing.
 */
function loadCSVFile(file, callback) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const text = e.target.result;
        const lines = text.split('\n').filter(line => line.trim() !== '');
        
        if (lines.length < 2) {
            alert("The CSV file must have a header and at least one data row.");
            return;
        }
        
        // Auto-detect delimiter
        const headerLine = lines[0];
        let delimiter = ',';
        if (headerLine.includes(';')) {
            const semicolonCount = (headerLine.match(/;/g) || []).length;
            const commaCount = (headerLine.match(/,/g) || []).length;
            if (semicolonCount > commaCount) {
                delimiter = ';';
            }
        }
        
        // Parse CSV
        HeliosState.tableData.headers = robustParseCSVRow(headerLine, delimiter);
        HeliosState.tableData.rows = lines.slice(1).map(row => {
            if (row.trim() === '') return null;
            return robustParseCSVRow(row, delimiter);
        }).filter(row => row !== null);
        
        // Reset state
        resetApplicationState();
        
        callback(file.name);
    };
    
    reader.onerror = () => alert("Error reading the file.");
    reader.readAsText(file);
}

/**
 * Resets the application state for a new dataset.
 */
function resetApplicationState() {
    HeliosState.targetColumnIndex = null;
    HeliosState.comparisonColumnIndices = [];
    HeliosState.datasetDescriptionText = '';
    HeliosState.isDataDiscretized = false;
    HeliosState.collapsibleStates = {};
}

// --- DATA TYPE DETECTION ---

/**
 * Determines if a column's data is predominantly numeric.
 * @param {number} columnIndex - The index of the column to check.
 * @returns {boolean} - True if the column is classified as numeric.
 */
function isColumnNumeric(columnIndex) {
    if (!HeliosState.tableData.rows || HeliosState.tableData.rows.length === 0) return false;
    
    const columnData = HeliosState.tableData.rows.map(row => row[columnIndex]);
    const validData = columnData.filter(val => val != null && val.toString().trim() !== '');
    
    if (validData.length === 0) return false;
    
    const numericCount = validData.filter(val => !isNaN(Number(val))).length;
    return (numericCount / validData.length) > 0.8;
}

/**
 * Checks if a non-numeric column is binary (exactly two unique values).
 * @param {number} columnIndex - The index of the column to check.
 * @returns {boolean} - True if the column is categorical and binary.
 */
function isColumnBinary(columnIndex) {
    if (isColumnNumeric(columnIndex)) {
        return false;
    }
    const uniqueValues = [...new Set(HeliosState.tableData.rows.map(row => row[columnIndex])
        .filter(val => val != null && val.toString().trim() !== ''))];
    return uniqueValues.length === 2;
}

/**
 * Differentiates between continuous numeric and binary numeric columns.
 * @param {number} columnIndex - The index of the column to check.
 * @returns {boolean} - True if the column is numeric with more than 2 unique values.
 */
function isTrueContinuous(columnIndex) {
    if (!isColumnNumeric(columnIndex)) {
        return false;
    }
    const uniqueValues = [...new Set(HeliosState.tableData.rows.map(row => row[columnIndex]))];
    return uniqueValues.length > 2;
}

// --- COLUMN OPERATIONS ---

/**
 * Sets or unsets the target column for analysis.
 * @param {number} index - The index of the column to be set as the target.
 */
function selectTargetColumn(index) {
    if (HeliosState.targetColumnIndex === index) {
        HeliosState.targetColumnIndex = null;
    } else {
        HeliosState.targetColumnIndex = index;
        if (HeliosState.comparisonColumnIndices.includes(index)) {
            HeliosState.comparisonColumnIndices = HeliosState.comparisonColumnIndices.filter(i => i !== index);
        }
    }
}

/**
 * Toggles a column for group comparison.
 * @param {number} index - The index of the column to toggle.
 */
function selectComparisonColumn(index) {
    if (!HeliosState.isDataDiscretized) {
        alert("Please discretize the numeric data before selecting comparison columns.");
        return;
    }
    
    const selectionIndex = HeliosState.comparisonColumnIndices.indexOf(index);
    if (selectionIndex > -1) {
        HeliosState.comparisonColumnIndices.splice(selectionIndex, 1);
    } else {
        HeliosState.comparisonColumnIndices.push(index);
    }
}

/**
 * Renames a column header.
 * @param {number} index - The index of the column to rename.
 * @param {string} newName - The new name for the column.
 */
function renameColumn(index, newName) {
    if (newName && newName !== HeliosState.tableData.headers[index]) {
        HeliosState.tableData.headers[index] = newName;
    }
}

/**
 * Deletes a column from the dataset.
 * @param {number} index - The index of the column to delete.
 */
function deleteColumn(index) {
    HeliosState.tableData.headers.splice(index, 1);
    
    // Adjust target index
    if (index === HeliosState.targetColumnIndex) {
        HeliosState.targetColumnIndex = null;
    } else if (HeliosState.targetColumnIndex !== null && index < HeliosState.targetColumnIndex) {
        HeliosState.targetColumnIndex--;
    }
    
    // Adjust comparison indices
    HeliosState.comparisonColumnIndices = HeliosState.comparisonColumnIndices
        .map(i => {
            if (i === index) return -1;
            if (i > index) return i - 1;
            return i;
        })
        .filter(i => i !== -1);
    
    HeliosState.tableData.rows.forEach(row => row.splice(index, 1));
}

/**
 * Maps a categorical column to binary values (0/1).
 * @param {number} columnIndex - The index of the column to map.
 */
function mapColumnToBinary(columnIndex) {
    if (isColumnNumeric(columnIndex)) {
        alert("This column is already numeric.");
        return;
    }
    
    const columnData = HeliosState.tableData.rows.map(row => row[columnIndex]);
    const uniqueValues = [...new Set(columnData.filter(val => val != null && val.toString().trim() !== ''))];
    
    let valueMap = {};
    let topTwoValues = [];
    
    if (uniqueValues.length < 2) {
        alert("This column does not have enough unique values to create a binary mapping.");
        return;
    } else if (uniqueValues.length === 2) {
        topTwoValues = uniqueValues;
        valueMap = {
            [topTwoValues[0]]: 0,
            [topTwoValues[1]]: 1
        };
    } else {
        const frequencies = columnData.reduce((acc, val) => {
            if (val != null && val.toString().trim() !== '') {
                acc[val] = (acc[val] || 0) + 1;
            }
            return acc;
        }, {});
        
        topTwoValues = Object.entries(frequencies)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 2)
            .map(([value]) => value);
        
        if (topTwoValues.length < 2) {
            alert("Could not determine the two most frequent categories. Please check your data.");
            return;
        }
        
        alert(`This column has multiple categories. Mapping the two most frequent:\n- "${topTwoValues[0]}" will be mapped to 0.\n- "${topTwoValues[1]}" will be mapped to 1.\nAll other values will be cleared.`);
        
        valueMap = {
            [topTwoValues[0]]: 0,
            [topTwoValues[1]]: 1
        };
    }
    
    const newRows = HeliosState.tableData.rows.map(row => {
        const newRow = [...row];
        const cellValue = newRow[columnIndex];
        
        if (cellValue in valueMap) {
            newRow[columnIndex] = valueMap[cellValue];
        } else if (uniqueValues.length > 2) {
            newRow[columnIndex] = '';
        }
        return newRow;
    });
    
    HeliosState.tableData.rows = newRows;
    alert(`Column "${HeliosState.tableData.headers[columnIndex]}" has been mapped.`);
}

// --- DATA DISCRETIZATION ---

/**
 * Discretizes continuous numeric columns into categorical bins based on quartiles.
 */
function discretizeData() {
    if (HeliosState.targetColumnIndex === null) {
        alert("Please select a target column before discretizing data.");
        return;
    }
    
    const newHeaders = [];
    const newRows = HeliosState.tableData.rows.map(() => []);
    const originalTargetHeader = HeliosState.tableData.headers[HeliosState.targetColumnIndex];
    
    HeliosState.tableData.headers.forEach((header, index) => {
        const isTarget = index === HeliosState.targetColumnIndex;
        const shouldDiscretize = isTrueContinuous(index) && !isTarget;
        
        if (shouldDiscretize) {
            const newHeaderName = `${header}_Class`;
            newHeaders.push(newHeaderName);
            
            const numericValues = HeliosState.tableData.rows
                .map(row => parseFloat(row[index]))
                .filter(v => !isNaN(v));
            
            if (numericValues.length === 0) {
                HeliosState.tableData.rows.forEach((row, rowIndex) => newRows[rowIndex].push('NA'));
                return;
            }
            
            const uniqueNumericValues = [...new Set(numericValues)];
            if (uniqueNumericValues.length <= 1) {
                HeliosState.tableData.rows.forEach((row, rowIndex) => 
                    newRows[rowIndex].push(String(uniqueNumericValues[0] || 'NA')));
                return;
            }
            
            numericValues.sort((a, b) => a - b);
            
            const getQuantile = (arr, q) => {
                const pos = (arr.length - 1) * q;
                const base = Math.floor(pos);
                const rest = pos - base;
                if (arr[base + 1] !== undefined) {
                    return arr[base] + rest * (arr[base + 1] - arr[base]);
                }
                return arr[base];
            };
            
            const q1 = getQuantile(numericValues, 0.25);
            const q2 = getQuantile(numericValues, 0.50);
            const q3 = getQuantile(numericValues, 0.75);
            
            const binEdges = [...new Set([
                Math.min(...numericValues), q1, q2, q3, Math.max(...numericValues)
            ])].sort((a, b) => a - b);
            
            const labels = [];
            for (let i = 0; i < binEdges.length - 1; i++) {
                labels.push(`${Math.trunc(binEdges[i])}-${Math.trunc(binEdges[i+1])}`);
            }
            
            HeliosState.tableData.rows.forEach((row, rowIndex) => {
                const val = parseFloat(row[index]);
                let binLabel = 'NA';
                
                if (!isNaN(val)) {
                    for (let i = 0; i < binEdges.length - 1; i++) {
                        if (i === binEdges.length - 2) {
                            if (val >= binEdges[i] && val <= binEdges[i+1]) {
                                binLabel = labels[i];
                                break;
                            }
                        } else {
                            if (val >= binEdges[i] && val < binEdges[i+1]) {
                                binLabel = labels[i];
                                break;
                            }
                        }
                    }
                }
                newRows[rowIndex].push(binLabel);
            });
        } else if (isColumnNumeric(index) && !isTrueContinuous(index) && !isTarget) {
            newHeaders.push(header);
            HeliosState.tableData.rows.forEach((row, rowIndex) => {
                newRows[rowIndex].push(String(row[index]));
            });
        } else {
            newHeaders.push(header);
            HeliosState.tableData.rows.forEach((row, rowIndex) => {
                newRows[rowIndex].push(row[index]);
            });
        }
    });
    
    HeliosState.tableData.headers = newHeaders;
    HeliosState.tableData.rows = newRows;
    HeliosState.targetColumnIndex = HeliosState.tableData.headers.indexOf(originalTargetHeader);
    HeliosState.isDataDiscretized = true;
}

// --- EXPORT STATE AND FUNCTIONS ---
window.HeliosCore = {
    state: HeliosState,
    loadCSVFile,
    isColumnNumeric,
    isColumnBinary,
    isTrueContinuous,
    selectTargetColumn,
    selectComparisonColumn,
    renameColumn,
    deleteColumn,
    mapColumnToBinary,
    discretizeData
};