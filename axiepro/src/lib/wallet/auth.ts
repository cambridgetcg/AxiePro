/**
 * Wallet authentication API functions.
 *
 * Handles challenge/verify flow for wallet-based authentication.
 */
import { apiClient } from '@/lib/api/client';

export interface ChallengeResponse {
  challenge_id: string;
  message: string;
  expires_at: string;
}

export interface VerifyResponse {
  token: string;
  expires_at: string;
  address: string;
}

/**
 * Request an authentication challenge for a wallet address.
 *
 * @param address - The wallet address requesting authentication
 * @returns Challenge data including the message to sign
 */
export async function requestChallenge(address: string): Promise<ChallengeResponse> {
  return apiClient<ChallengeResponse>('/auth/challenge', {
    method: 'POST',
    body: JSON.stringify({ address: address.toLowerCase() }),
  });
}

/**
 * Verify a signed challenge and receive a JWT token.
 *
 * @param challengeId - The challenge ID from requestChallenge
 * @param signature - The wallet signature of the challenge message
 * @returns JWT token and expiration
 */
export async function verifySignature(
  challengeId: string,
  signature: string
): Promise<VerifyResponse> {
  return apiClient<VerifyResponse>('/auth/verify', {
    method: 'POST',
    body: JSON.stringify({
      challenge_id: challengeId,
      signature,
    }),
  });
}

/**
 * Cancel an unused challenge.
 *
 * @param challengeId - The challenge ID to cancel
 */
export async function cancelChallenge(challengeId: string): Promise<void> {
  await apiClient(`/auth/challenge/${challengeId}`, {
    method: 'DELETE',
  });
}
