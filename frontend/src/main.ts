// Projet : FFE Chess Agent : Proof of Concept

import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent }         from './app/app.component';
import { appConfig }            from './app/app.config';

bootstrapApplication(AppComponent, appConfig)
  .catch(err => console.error(err));
