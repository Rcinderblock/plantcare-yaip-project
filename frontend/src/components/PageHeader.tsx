import { Stack, Typography } from "@mui/material";

export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Stack spacing={1} sx={{ mb: 3 }}>
      <Typography variant="overline" color="secondary" fontWeight={700}>
        PlantCare MVP
      </Typography>
      <Typography variant="h3" component="h1">
        {title}
      </Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
        {subtitle}
      </Typography>
    </Stack>
  );
}
