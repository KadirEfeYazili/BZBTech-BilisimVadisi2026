import type { Config } from "tailwindcss";

/**
 * Tema, katılım bankacılığının kurumsal görsel diline dayanır: yeşil-turkuaz
 * palet, düşük doygunluk, gölge yerine 1px kenarlık.
 *
 * ⚠️ Mor/indigo/pembe gradient BİLİNÇLİ olarak tanımlanmamıştır — bunlar
 * yapay zekâ ürünlerinin klişesidir ve bu bir finansal kurum iç aracıdır.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          900: "var(--brand-900)",
          700: "var(--brand-700)",
          500: "var(--brand-500)",
        },
        teal: {
          500: "var(--teal-500)",
          100: "var(--teal-100)",
        },
        neutral: {
          50: "var(--neutral-50)",
        },
        surface: "var(--surface)",
        border: "var(--border)",
        text: {
          900: "var(--text-900)",
          500: "var(--text-500)",
        },
        warn: {
          600: "var(--warn-600)",
        },
        danger: {
          600: "var(--danger-600)",
        },
      },
      borderRadius: {
        // §10.2: border-radius 12px'i AŞMAZ.
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "12px",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      fontSize: {
        // Gövde 14-15px (§10.2)
        base: ["14px", "20px"],
        sm: ["13px", "18px"],
        xs: ["12px", "16px"],
      },
      spacing: {
        // Yoğun tablo satır yüksekliği 40-44px
        row: "42px",
      },
      transitionDuration: {
        // Geçişler 150ms'i aşmaz.
        DEFAULT: "150ms",
      },
    },
  },
  plugins: [],
} satisfies Config;
