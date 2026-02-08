# NixOS Scheduling Setup

To run the `daily-paper-feed` script every day at 8:00 AM on NixOS, you can use a Systemd service and timer. 

Since you likely want to run this as your user (to access your home directory and environment), I recommend using **Home Manager**. If you don't use Home Manager, you can add it to your system configuration (`/etc/nixos/configuration.nix`) as a system service, but you'll need to be careful with paths and permissions.

## Option 1: Home Manager (Recommended)

Add the following to your `home.nix`:

```nix
systemd.user.services.daily-paper-feed = {
  Unit = {
    Description = "Daily Arxiv Paper Feed Generator";
  };
  Service = {
    Type = "oneshot";
    # Point this to your repository path
    WorkingDirectory = "/home/nguyen/daily-arXiv-ai-enhanced";
    # Ensure all required environment variables are set here or in the script
    Environment = [
      "PATH=/run/current-system/sw/bin:/home/nguyen/.nix-profile/bin"
      "GOOGLE_API_KEY=your_api_key_here"  # Or load from a file/sops-nix
      "EMAIL_SENDER=your_email@gmail.com"
      "EMAIL_PASSWORD=your_app_password"
      "EMAIL_RECEIVER=your_email@gmail.com"
    ];
    ExecStart = "${pkgs.bash}/bin/bash ./run_custom.sh";
  };
};

systemd.user.timers.daily-paper-feed = {
  Unit = {
    Description = "Run Daily Paper Feed at 8 AM";
  };
  Timer = {
    OnCalendar = "*-*-* 08:00:00";
    Persistent = true; # Run immediately if missed (e.g. computer was off)
  };
  Install = {
    WantedBy = [ "timers.target" ];
  };
};
```

## Option 2: System Configuration (configuration.nix)

If you prefer a system-wide service (running as a specific user):

```nix
systemd.services.daily-paper-feed = {
  description = "Daily Arxiv Paper Feed Generator";
  serviceConfig = {
    Type = "oneshot";
    User = "yourusername";
    WorkingDirectory = "/home/yourusername/path/to/daily_paper_feed";
    ExecStart = "${pkgs.bash}/bin/bash ./run_custom.sh";
  };
  environment = {
    GOOGLE_API_KEY = "your_api_key_here";
    EMAIL_SENDER = "your_email@gmail.com";
    EMAIL_PASSWORD = "your_app_password";
    EMAIL_RECEIVER = "your_email@gmail.com";
  };
};

systemd.timers.daily-paper-feed = {
  description = "Run Daily Paper Feed at 8 AM";
  wantedBy = [ "timers.target" ];
  timerConfig = {
    OnCalendar = "*-*-* 08:00:00";
    Persistent = true;
  };
};
```

## Prerequisite: Secrets Management
For `GOOGLE_API_KEY` and email passwords, **do not commit them to git**. 
- In **run_custom.sh**, we load `.env` from the `ai/` directory. Ensure `ai/.env` exists on your server.
- The `send_email.py` script expects `EMAIL_SENDER` and `EMAIL_PASSWORD` as env vars. You can set them in the systemd unit (as shown above) or load them in `run_custom.sh`.

## Email Configuration
To enable the email feature, you must set:
- `EMAIL_SENDER`: Your email address (e.g., `user@gmail.com`).
- `EMAIL_PASSWORD`: Your App Password (if using Gmail with 2FA, generate one at https://myaccount.google.com/apppasswords).
- `EMAIL_RECEIVER`: (Optional) Defaults to sender.

> **Note on Gmail**: This script uses **SMTP** to send emails, not POP3 (which is for receiving and being deprecated). SMTP with App Passwords is fully supported and secure.
