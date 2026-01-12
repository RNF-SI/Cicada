import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-registration-pending',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule],
  template: `
    <div class="pending-page">
      <div class="pending-container">
        <div class="pending-content">
          <div class="icon-circle">
            <i class="fi fi-rr-hourglass-end"></i>
          </div>

          <h1>Inscription en attente</h1>

          <p class="message">
            Votre demande d'inscription a bien ete enregistree.
          </p>

          <p class="details">
            Un administrateur de l'organisme que vous avez choisi va examiner votre demande.
            Vous recevrez un email a l'adresse fournie une fois votre inscription validee.
          </p>

          <div class="info-box">
            <i class="fi fi-rr-info"></i>
            <p>
              Le delai de traitement peut varier selon la disponibilite des administrateurs.
              N'hesitez pas a les contacter directement si necessaire.
            </p>
          </div>

          <div class="actions">
            <a mat-flat-button color="primary" routerLink="/accueil">
              <i class="fi fi-rr-home"></i>
              Retour a l'accueil
            </a>
            <a mat-stroked-button routerLink="/auth/login">
              <i class="fi fi-rr-sign-in-alt"></i>
              Se connecter
            </a>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .pending-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      padding: 24px;
    }

    .pending-container {
      width: 100%;
      max-width: 520px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
      padding: 48px 40px;
    }

    .pending-content {
      text-align: center;
    }

    .icon-circle {
      width: 80px;
      height: 80px;
      margin: 0 auto 24px;
      background: linear-gradient(135deg, #FEC180 0%, #FA9965 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;

      i {
        font-size: 36px;
        color: white;
      }
    }

    h1 {
      font-family: 'Nunito', sans-serif;
      font-size: 28px;
      font-weight: 700;
      color: #025359;
      margin: 0 0 16px 0;
    }

    .message {
      font-size: 16px;
      color: #374151;
      margin: 0 0 12px 0;
      font-weight: 600;
    }

    .details {
      font-size: 14px;
      color: #6b7280;
      margin: 0 0 24px 0;
      line-height: 1.6;
    }

    .info-box {
      display: flex;
      gap: 12px;
      padding: 16px;
      background: #f0f9ff;
      border: 1px solid #bae6fd;
      border-radius: 8px;
      color: #0369a1;
      font-size: 13px;
      text-align: left;
      margin-bottom: 32px;

      i {
        font-size: 18px;
        flex-shrink: 0;
        margin-top: 2px;
      }

      p {
        margin: 0;
        line-height: 1.5;
      }
    }

    .actions {
      display: flex;
      flex-direction: column;
      gap: 12px;

      a {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        height: 48px;
        font-size: 15px;
        font-weight: 600;
        border-radius: 8px;

        i {
          font-size: 16px;
        }
      }
    }

    @media (max-width: 480px) {
      .pending-container {
        padding: 32px 24px;
      }

      h1 {
        font-size: 24px;
      }
    }
  `]
})
export class RegistrationPendingComponent {}
