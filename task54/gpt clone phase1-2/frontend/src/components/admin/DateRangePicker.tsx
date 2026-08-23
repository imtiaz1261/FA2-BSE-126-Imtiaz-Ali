/**
 * Date Range Picker Component
 *
 * Allows selecting predefined or custom date ranges
 */

import React, { useState } from "react";
import { format, subDays } from "date-fns";
import { Calendar } from "lucide-react";

interface DateRange {
  start_date: string;
  end_date: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

const PRESETS = [
  {
    label: "Today",
    getValue: () => {
      const today = new Date();
      return {
        start_date: format(today, "yyyy-MM-dd"),
        end_date: format(today, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "7 days",
    getValue: () => {
      const end = new Date();
      const start = subDays(end, 7);
      return {
        start_date: format(start, "yyyy-MM-dd"),
        end_date: format(end, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "30 days",
    getValue: () => {
      const end = new Date();
      const start = subDays(end, 30);
      return {
        start_date: format(start, "yyyy-MM-dd"),
        end_date: format(end, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "90 days",
    getValue: () => {
      const end = new Date();
      const start = subDays(end, 90);
      return {
        start_date: format(start, "yyyy-MM-dd"),
        end_date: format(end, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "12 months",
    getValue: () => {
      const end = new Date();
      const start = subDays(end, 365);
      return {
        start_date: format(start, "yyyy-MM-dd"),
        end_date: format(end, "yyyy-MM-dd"),
      };
    },
  },
];

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  value,
  onChange,
}) => {
  const [open, setOpen] = useState(false);

  const handlePreset = (preset: (typeof PRESETS)[0]) => {
    onChange(preset.getValue());
    setOpen(false);
  };

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      start_date: e.target.value,
    });
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      end_date: e.target.value,
    });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2"
      >
        <Calendar size={18} />
        {value.start_date} to {value.end_date}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4 w-96">
          {/* Presets */}
          <div className="mb-4 pb-4 border-b border-gray-200">
            <p className="text-sm font-medium text-gray-700 mb-2">Presets</p>
            <div className="grid grid-cols-5 gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => handlePreset(preset)}
                  className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom range */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={value.start_date}
                onChange={handleStartChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={value.end_date}
                onChange={handleEndChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="mt-4 pt-4 border-t border-gray-200 flex gap-2 justify-end">
            <button
              onClick={() => setOpen(false)}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => setOpen(false)}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DateRangePicker;
