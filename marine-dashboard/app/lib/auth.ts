import { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "select_account",
          hd: 'vitstudent.ac.in',
        },
      },
    }),
  ],
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error', 
  },
  callbacks: {
    async signIn({ user, account }) {
      console.log('Sign-in attempt:', user.email);
      if (user.email?.endsWith('@vitstudent.ac.in')) {
        console.log('User authenticated successfully:', user.email);
        return true;
      } else {
        console.log('Access denied for:', user.email);
        return false;
      }
    },
    async redirect({ url, baseUrl }) {
      console.log('Redirect callback - URL:', url, 'Base URL:', baseUrl);
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      else if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
    async session({ session, token }) {
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};
