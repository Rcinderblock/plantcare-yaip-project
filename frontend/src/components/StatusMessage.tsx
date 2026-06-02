import { Alert } from "@mui/material";

export function StatusMessage({ error, success }: { error?: string; success?: string }) {
  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (success) {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        {success}
      </Alert>
    );
  }

  return null;
}
