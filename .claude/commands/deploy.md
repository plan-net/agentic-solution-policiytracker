# Deploy Command

Perform a quick deployment cycle for the Political Monitoring Agent:

1. Run `just dev-quick` to redeploy the Kodosumi application
2. Wait a few seconds for deployment to complete
3. Check if Kodosumi is responding at http://localhost:3370/health
4. Display the deployment status and access URLs:
   - Kodosumi Admin: http://localhost:3370 (admin/admin)
   - Ray Dashboard: http://localhost:8265  
   - App Endpoint: http://localhost:8001/political-analysis
5. If deployment fails, show the recent Kodosumi logs using `just kodosumi-logs | tail -20`

Provide clear status messages throughout the process and use appropriate emojis (🚀, ✅, ❌) to indicate success or failure states.