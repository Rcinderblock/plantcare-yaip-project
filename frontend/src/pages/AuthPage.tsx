import { Box, Button, Card, CardContent, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { StatusMessage } from "../components/StatusMessage";
import { useAuth } from "../context/AuthContext";

interface LoginForm {
  username: string;
  password: string;
}

interface RegisterForm extends LoginForm {
  email: string;
}

export function AuthPage() {
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const loginForm = useForm<LoginForm>();
  const registerForm = useForm<RegisterForm>();
  const redirectTo = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/plants";

  const submitLogin = loginForm.handleSubmit(async (values) => {
    setError("");
    try {
      await signIn(values.username, values.password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти");
    }
  });

  const submitRegister = registerForm.handleSubmit(async (values) => {
    setError("");
    try {
      await signUp(values.username, values.email, values.password);
      navigate("/plants", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось зарегистрироваться");
    }
  });

  return (
    <Box>
      <PageHeader
        title="Вход и регистрация"
        subtitle="Авторизация защищает личные растения, коллекции, календарь ухода и массовый импорт."
      />
      <Card sx={{ maxWidth: 560 }}>
        <CardContent>
          <Tabs value={tab} onChange={(_, value: number) => setTab(value)} sx={{ mb: 3 }}>
            <Tab label="Войти" />
            <Tab label="Создать аккаунт" />
          </Tabs>
          <StatusMessage error={error} />
          {tab === 0 ? (
            <Stack component="form" spacing={2} onSubmit={submitLogin}>
              <TextField label="Логин" autoComplete="username" {...loginForm.register("username", { required: true })} />
              <TextField
                label="Пароль"
                type="password"
                autoComplete="current-password"
                {...loginForm.register("password", { required: true })}
              />
              <Button type="submit" disabled={loginForm.formState.isSubmitting} variant="contained">
                Войти
              </Button>
            </Stack>
          ) : (
            <Stack component="form" spacing={2} onSubmit={submitRegister}>
              <Typography color="text.secondary">
                Для демо подойдет пароль длиной от 8 символов, например `plant-pass`.
              </Typography>
              <TextField label="Логин" autoComplete="username" {...registerForm.register("username", { required: true })} />
              <TextField label="Email" type="email" {...registerForm.register("email", { required: true })} />
              <TextField
                label="Пароль"
                type="password"
                autoComplete="new-password"
                {...registerForm.register("password", { required: true, minLength: 8 })}
              />
              <Button type="submit" disabled={registerForm.formState.isSubmitting} variant="contained">
                Зарегистрироваться
              </Button>
            </Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
