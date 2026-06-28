# Public demo deploy (Vercel, no backend, no login)

This deploys **only the frontend** with `NEXT_PUBLIC_DEMO_MODE=1`, so it renders the built-in
demo data as a complete, no-login walkthrough. The real app (with your data and the pilot
login) stays private on its own host — never put that URL or password in the public repo.

## One-time setup (Vercel dashboard)

1. Go to <https://vercel.com> and sign in with GitHub.
2. **Add New… → Project**, then import `rosscyking1115/cited-market-brief-agent`.
3. In the configure screen:
   - **Root Directory**: set to `frontend` (click *Edit* and pick the folder).
   - **Framework Preset**: Next.js (auto-detected).
   - **Environment Variables**: add one —
     - Name: `NEXT_PUBLIC_DEMO_MODE`
     - Value: `1`
   - Do **not** set `BACKEND_ORIGIN` / `API_URL` (leaving them unset keeps it in demo mode).
4. **Deploy**. You'll get a URL like `https://cited-market-brief-agent.vercel.app`.

That's it. Every push to the default branch redeploys automatically.

## CLI alternative

```bash
cd frontend
npx vercel login          # opens the browser once
npx vercel --prod -e NEXT_PUBLIC_DEMO_MODE=1
```

## After deploying

- Open the URL, accept the region prompt, and click through TW / KR / UK / EU. The radar,
  news, ETF attribution, and the evidence brief all render with demo data; no login.
- Add the link to `README.md` under a short **Live demo** line, e.g.:
  ```markdown
  ## Live demo
  [cited-market-brief-agent.vercel.app](https://cited-market-brief-agent.vercel.app) — demo data, no login.
  ```

## What demo mode changes

- Server render skips all backend calls and serves the demo dataset directly.
- Client components don't poll `/api` (no failing requests).
- The Taiwan ETF tool shows a populated demo result + a banner noting that the interactive
  actions (parse, TWSE fill, save) need a live backend.
