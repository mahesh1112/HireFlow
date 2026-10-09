import apiClient from "./client";
import type { AuthResponse, LoginCredentials, RegisterCredentials, User } from "@/lib/types";

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const formData = new URLSearchParams();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);
    const { data } = await apiClient.post<AuthResponse>("/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },

  register: async (credentials: RegisterCredentials): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>("/auth/register", credentials);
    return data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  getProfile: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/auth/profile");
    return data;
  },

  refreshToken: async (token: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>("/auth/refresh-token", { token });
    return data;
  },
};
