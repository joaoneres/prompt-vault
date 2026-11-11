import type {
  CreatePromptRequest,
  PromptDetailResponse,
  PromptResponse,
  PromptVersionResponse,
  VersionDiffResponse,
} from "../types";
import { http } from "./client";

// Endpoints from openapi.json (the API's Swagger). Responses are the DTOs of the gateway.

/** GET /prompts/active */
export const listActivePrompts = async (): Promise<PromptResponse[]> =>
  (await http.get<PromptResponse[]>("/prompts/active")).data;

/** GET /prompts/{prompt_id} */
export const getPrompt = async (promptId: string): Promise<PromptDetailResponse> =>
  (await http.get<PromptDetailResponse>(`/prompts/${promptId}`)).data;

/** POST /prompts */
export const createPrompt = async (body: CreatePromptRequest): Promise<PromptResponse> =>
  (await http.post<PromptResponse>("/prompts", body)).data;

/** PUT /prompts/{prompt_id}/content: creates a new version and activates it. */
export const updateContent = async (promptId: string, content: string): Promise<PromptVersionResponse> =>
  (await http.put<PromptVersionResponse>(`/prompts/${promptId}/content`, { content })).data;

/** POST /prompts/{prompt_id}/compare: line diff between two version numbers (before -> after). */
export const compareVersions = async (
  promptId: string,
  fromVersion: number,
  toVersion: number,
): Promise<VersionDiffResponse> =>
  (
    await http.post<VersionDiffResponse>(`/prompts/${promptId}/compare`, {
      from_version: fromVersion,
      to_version: toVersion,
    })
  ).data;
