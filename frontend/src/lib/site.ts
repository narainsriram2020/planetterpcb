// Public site identity, shared by metadata, the sitemap, and the share image.
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://terpguide.vercel.app").replace(/\/$/, "");
export const SITE_NAME = "TerpGuide";
export const SITE_TITLE = "TerpGuide: who to take at UMD, backed by PlanetTerp data";
export const SITE_DESCRIPTION =
  "Ask who to take for a UMD class, how hard a course is, or which GenEds grade nicest. " +
  "TerpGuide pulls PlanetTerp grade distributions, professor ratings, and reviews and shows the numbers behind every answer.";
